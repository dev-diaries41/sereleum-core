import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from sereleum.constants.test_data import robot_prompts
from smartscan.embeds.helpers import generate_prototype_embedding
from smartscan.models.model_manager import ModelManager

# Prototype fusion with a domain seed is a lightweight form of domain adaptation. 
# It can significantly improve retrieval alignment when the seed accurately represents the target corpus. 
# The choice of seed is more important than the number of seeds, and overly broad or mixed seeds can reduce specificity.
#  For this robotics dataset, a focused seed ("mobile robots") outperforms broader concepts and multi-seed fusion.


mm = ModelManager()
text_embedder = mm.get_text_embedder("all-minilm-l6-v2")
text_embedder.init()


SEEDS = [
    "robots",
    "robotics",
    "autonomous systems",
    "industrial automation",
    "machine intelligence",
    "robot control",
    "mobile robots",
]

MULTI_SEEDS = [
    ["mobile robots", "robotics"],
    ["mobile robots", "robot control"],
    ["mobile robots", "autonomous systems"],
    ["mobile robots", "robotics", "autonomous systems"],
]


ALPHAS = np.linspace(0.4, 1.0, 7)


ROBOTICS_QUERIES = [
    "ROS 2 localization using wheel odometry and LiDAR",
    "Robot motion planning around moving humans",
    "Vision-guided robotic arm grasp planning",
    "Differential drive trajectory tracking controller",
    "Visual-inertial SLAM for autonomous drones",
    "Legged robot balance on uneven terrain",
    "Industrial robot inspection with machine vision",
    "Multi-robot map merging over unreliable networks",
]


ENGINEERING_QUERIES = [
    "PID tuning for a brushless motor controller",
    "Sensor fusion for autonomous vehicle navigation",
    "Industrial automation using programmable logic controllers",
    "State estimation for mechatronic control systems",
    "Real-time control of electromechanical actuators",
    "Kalman filtering for inertial navigation systems",
]


UNRELATED_QUERIES = [
    "Investment strategies during rising interest rates",
    "Diagnosing bacterial pneumonia in elderly patients",
    "Traditional Italian pasta recipes with seafood",
    "Retirement portfolio diversification techniques",
    "How to bake sourdough bread at home",
]


def fuse(text_embed, seed_embed, alpha):
    fused = alpha * text_embed + (1 - alpha) * seed_embed
    return fused / np.linalg.norm(fused)


def mean_similarity(prototype, queries):
    return float(
        np.mean(
            [
                np.dot(prototype, text_embedder.embed(query)[0])
                for query in queries
            ]
        )
    )


def build_standard_prototype():
    embeds = np.stack(
        [text_embedder.embed(text)[0] for text in robot_prompts]
    )
    return generate_prototype_embedding(embeds)


def build_single_seed_prototype(seed, alpha):
    seed_embed = text_embedder.embed(seed)[0]

    fused = []

    for text in robot_prompts:
        text_embed = text_embedder.embed(text)[0]
        fused.append(
            fuse(text_embed, seed_embed, alpha)
        )

    return generate_prototype_embedding(np.stack(fused))


def build_multi_seed_prototype(seeds, alpha):
    seed_embeds = np.stack(
        [
            text_embedder.embed(seed)[0]
            for seed in seeds
        ]
    )

    seed_prototype = generate_prototype_embedding(seed_embeds)

    fused = []

    for text in robot_prompts:
        text_embed = text_embedder.embed(text)[0]
        fused.append(
            fuse(text_embed, seed_prototype, alpha)
        )

    return generate_prototype_embedding(np.stack(fused))


def evaluate(prototype):
    robotics = mean_similarity(prototype, ROBOTICS_QUERIES)
    engineering = mean_similarity(prototype, ENGINEERING_QUERIES)
    unrelated = mean_similarity(prototype, UNRELATED_QUERIES)

    return {
        "robotics": robotics,
        "engineering": engineering,
        "unrelated": unrelated,
        "gap": robotics - unrelated,
    }


def test_standard_baseline():

    result = evaluate(
        build_standard_prototype()
    )

    print("\nSTANDARD")
    print(result)

    assert result["robotics"] > result["unrelated"]


def test_single_seed_sweep():

    results = []

    for seed in SEEDS:
        for alpha in ALPHAS:

            result = evaluate(
                build_single_seed_prototype(
                    seed,
                    alpha
                )
            )

            result.update(
                {
                    "seed": seed,
                    "alpha": alpha,
                }
            )

            results.append(result)

            print(
                f"{seed:25s} "
                f"alpha={alpha:.2f} "
                f"robotics={result['robotics']:.4f} "
                f"engineering={result['engineering']:.4f} "
                f"unrelated={result['unrelated']:.4f} "
                f"gap={result['gap']:.4f}"
            )


    best = max(
        results,
        key=lambda x: x["gap"]
    )

    print("\nBEST SINGLE SEED")
    print(best)

    assert best["gap"] > 0

    plt.figure(figsize=(10, 6))

    for seed in SEEDS:

        subset = [
            x for x in results
            if x["seed"] == seed
        ]

        plt.plot(
            [x["alpha"] for x in subset],
            [x["gap"] for x in subset],
            marker="o",
            label=seed,
        )

    plt.xlabel("alpha")
    plt.ylabel("Robotics - Unrelated similarity")
    plt.title("Single Seed Prototype Optimization")
    plt.grid(True)
    plt.legend()

    output = Path("single_seed_sweep.png")

    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()

    print(output.resolve())


def test_multi_seed_fusion():

    results = []

    for seeds in MULTI_SEEDS:

        for alpha in ALPHAS:

            result = evaluate(
                build_multi_seed_prototype(
                    seeds,
                    alpha
                )
            )

            result.update(
                {
                    "seeds": seeds,
                    "alpha": alpha,
                }
            )

            results.append(result)

            print(
                f"{seeds} "
                f"alpha={alpha:.2f} "
                f"gap={result['gap']:.4f}"
            )


    best = max(
        results,
        key=lambda x: x["gap"]
    )

    print("\nBEST MULTI SEED")
    print(best)

    assert best["gap"] > 0


def test_multi_seed_preserves_domain_improvement():

    baseline = evaluate(
        build_standard_prototype()
    )

    multi = max(
        [
            evaluate(
                build_multi_seed_prototype(
                    seeds,
                    alpha
                )
            )
            for seeds in MULTI_SEEDS
            for alpha in ALPHAS
        ],
        key=lambda x: x["gap"]
    )

    print("\nBASELINE")
    print(baseline)

    print("\nBEST MULTI")
    print(multi)

    assert multi["gap"] > baseline["gap"]
    assert multi["robotics"] > baseline["robotics"]