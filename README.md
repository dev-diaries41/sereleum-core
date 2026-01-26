# Sereleum

Sereleum is a prompts analytics platform that allows businesses to turn user prompts into actionable insights. It enables uncovering semantic patterns, and optimising LLM-powered products. 

## Core Features

Sereleum focuses on 2 core features that deliver high value to businesses with LLM-powered products.

1. **Clustering prompts**
   * Automatically groups similar prompts and labels clusters to reveal the most popular business use cases or key user experiences.

2. **Token Usage by Cluster (top 5 clusters only)**
   * Tracks **token consumption and cost per use case**, helping businesses understand which use cases are driving LLM costs. Only the top 5 clusters are shown, as these represent the most significant, high-impact use cases and focusing on them reduces computational load while highlighting what matters most.

## Use Cases

* **Use Case Segmentation and Discoverability:** See exactly how users are engaging with your product.
  *Example:* Sereleum reveals that users frequently ask “how to automate reporting,” indicating "reporting automation" is a core workflow. Teams can prioritize improving that experience.

* **Optimize prompt templates:** Adapt prompts to get better results based on real interactions.
  *Example:* In a customer support chatbot, Sereleum shows users often ask “How do I cancel my subscription?” You tweak templates to provide clearer, faster instructions, reducing support tickets.

* **Refine system prompts:** Make the AI smarter by aligning it with what users actually want.
  *Example:* Your AI writing assistant produces overly formal outputs, but Sereleum shows users frequently request casual, blog-style content. You adjust the system prompt to better match user tone.

* **Cost and efficiency optimization:** Identify expensive prompts and streamline them.
  *Example:* Some analytics prompts pull huge datasets unnecessarily. Sereleum highlights the costliest prompts, allowing you to optimize them and save money.

## Design choices

* Model: MiniLM-6 quant onnxruntime model
* Max token length: MiniLM-l6 tokenizer used max length of 512 instead of 128
    - Pro: This improves cluster accuracy by avoiding loss of context when embedding large prompts
    - Con: This increases indexing time (batch embed generation and storage) by up to 4x
    - Bench marks: 50 prompts of character length ~ 500, using the 512 tokenizer length takes ~3s, on CPU with 16 cores
* Since cluster accuracy is pivotal for the features mentioned above 512 is used instead of 128 even though in increases processing time.
    