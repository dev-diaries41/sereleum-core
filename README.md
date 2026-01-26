# Sereleum

Sereleum is a prompts analytics platform that allows businesses to turn user prompts into actionable insights. It enables uncovering semantic patterns, and optimising LLM-powered products. 

## Core Features

Sereleum focuses on analytics-driven controls that turn raw user prompts into standardized, high-quality, and cost-efficient interactions.

### 1. Prompt Clustering & Intent Discovery

Automatically groups semantically similar prompts and labels clusters to surface **dominant user intents and workflows**.

**What this enables:**

* Clear visibility into how users actually use your LLM-powered product
* Identification of repeatable, high-value use cases suitable for standardization
* Identify core product workflows

---

### 2. Token Usage & Cost by Cluster (Top 5)

Tracks token consumption and cost at the **use-case level**, focusing on the top 5 clusters that drive the majority of spend and traffic.

**Why top 5 only:**

* Captures the highest-impact intents
* Reduces noise and computational overhead
* Directs optimization efforts where ROI is highest

**What this enables:**

* Immediate visibility into which user intents are most expensive
* Prioritization of clusters for prompt optimization and templating

---

### 3. Cluster-Driven Prompt Template Discovery

Identifies clusters where **prompt structure can be standardized** to improve quality, consistency, and cost efficiency.

Instead of manually guessing which prompts need templates, Sereleum surfaces **template candidates** based on:

* High prompt repetition
* High token usage
* High variance in user phrasing for the same intent

**What this enables:**

* Converting dominant clusters into reusable prompt templates
* Reducing output variance across users
* Lowering token usage by constraining unnecessary verbosity
* Turning free-form chat into reliable product workflows

---

### 4. Feedback Loop: Measure Template Impact

Once templates are introduced, Sereleum tracks changes at the cluster level:

* Token usage before vs after templating
* Prompt length reduction
* Shift in cluster composition

This closes the loop between **observation → intervention → measurement**.

---

## Use Cases

### Use Case Segmentation & Discoverability

Understand exactly how users interact with your product at the intent level.

**Example:**
Sereleum reveals a dominant cluster around “production ML system design.” The team recognizes this as a core workflow rather than an edge case and invests in improving that experience.

---

### Prompt Template Optimization for Core Workflows

Use real prompt data to design templates that improve outputs and reduce user effort.

**Example:**
A customer support chatbot shows a large cluster for “cancel subscription.” Sereleum flags it as a high-volume, low-variance intent. The team introduces a structured template, reducing response time, token usage, and support tickets.

---

### System Prompt Refinement Based on Observed Demand

Align system-level behavior with actual user needs instead of assumptions.

**Example:**
Clusters show users consistently asking for casual, blog-style writing despite a formal system prompt. The team updates the system prompt and observes reduced rewrites and lower average token usage per request.

---

### Cost Control Through Cluster-Level Optimization

Identify which use cases drive disproportionate LLM costs and intervene surgically.

**Example:**
Analytics queries form a top-cost cluster due to overly verbose prompts. Sereleum surfaces this cluster as a template candidate. After introducing a constrained template, costs drop without degrading output quality.

---

### Turning Chat Into Product Workflows

Move from unstructured chat to reliable, repeatable product experiences.

**Example:**
An internal AI assistant shows repeated but inconsistently phrased prompts for “generate quarterly report insights.” Sereleum clusters them, surfaces the intent, and enables the team to ship a guided prompt template that becomes a first-class feature.

---

Sereleum enables businesses to treat prompts as **measurable, optimizable product interfaces**.


## Design choices

* Model: MiniLM-6 quant onnxruntime model
* Max token length: MiniLM-l6 tokenizer used max length of 512 instead of 128
    - Pro: This improves cluster accuracy by avoiding loss of context when embedding large prompts
    - Con: This increases indexing time (batch embed generation and storage) by up to 4x
    - Bench marks: 50 prompts of character length ~ 500, using the 512 tokenizer length takes ~3s, on CPU with 16 cores
* Since cluster accuracy is pivotal for the features mentioned above 512 is used instead of 128 even though in increases processing time.
    