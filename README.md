# Sereleum

Sereleum is a business-focused LLM analytics platform that turns real user prompts into actionable insights, optimized templates, cost analysis, and compliance monitoring.


## Core Features

1. **Cluster Prompts**

   * Automatically groups similar prompts and labels them to reveal the **most popular business use cases**.

2. **Token Usage by Cluster (only for top 5 clusters for)**

   * Tracks **token consumption and cost per use case**, helping teams identify expensive workflows and optimize budgets.
   * Only the top 5 clusters are shown, as these represent the most significant, high-impact use cases and focusing on them reduces computational load while highlighting what matters most.

## Design choices
* Model: MiniLM-6 quant onnxruntime model
* Max token length: MiniLM-l6 tokenizer used max length of 512 instead of 128
    - Pro: This improves cluster accuracy by avoiding loss of context when embedding large prompts
    - Con: This increases indexing time (batch embed generation and storage) by up to 4x
    - Bench marks: 50 prompts of character length ~ 500, using the 512 tokenizer length takes ~3s, on CPU with 16 cores
* Since cluster accuracy is pivotal for the features mentioned above 512 is used instead of 128 even though in increases processing time.
    