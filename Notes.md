This is an incredibly rigorous and ambitious problem statement, but tackling a multimodal, agentic architecture for ISRO is a high-impact challenge. Navigating the complexities of satellite imagery analysis, especially having previously developed hybrid deep learning models for ISRO competitions, provides a massive architectural advantage here. Combining that practical competitive experience with a strong foundation in computer vision, remote sensing, and natural language processing is exactly what this Vision-Language Model (VLM) orchestration requires.

Here is a strategic breakdown to help you structure your approach to "Problem_Statement.md":

### Core Architectural Requirements

SatQuery AI is not about training one massive model; it is an agentic, query-driven framework. Your system needs to accomplish the following:

* **Interpret and Route:** The agentic controller must analyze natural language queries and automatically select the appropriate specialist tool from a predefined registry.


* **Handle Multimodal Inputs:** The backend must process single optical/SAR images, co-registered optical-SAR pairs, and bi-temporal image pairs.


* **Perform Domain Adaptation:** You must fine-tune at least one visual or vision-language component using the BigEarthNet.txt dataset or similar open-source training data.



### Strategic Implementation Phases

When managing the development workflow for your team, dividing the pipeline into distinct tasks will keep the project modular:

* **Model Adaptation:** Begin by adapting image-text representations to multisensor remote-sensing data to ensure the models understand domain-specific terminology.


* **Specialist Tooling:** Develop or integrate specific modules for Visual Question Answering (which is a mandatory baseline), alongside either captioning or region grounding, and multitemporal change analysis.


* **Agentic Orchestration:** Build the core controller to validate inputs (checking format and modality), execute the workflow, and fuse textual and spatial outputs into a final evidence-grounded response.


* **Frontend Integration:** The final deliverable must be an interactive GUI or web application that provides visual evidence, confidence information, and an auditable execution trace.



### Critical Pitfalls to Avoid

* **Generic Models:** Relying solely on a general-purpose LLM or VLM without remote-sensing adaptation will automatically fail to satisfy the core requirements.


* **Blind Spots in Evaluation:** The final ISRO/SAC evaluation dataset will heavily test the system using co-registered Cartosat-2S optical and RISAT SAR pairs with undisclosed annotations.



Which specific agentic framework or routing logic are you considering to orchestrate the handoffs between the NLP query interpretation and the computer vision specialist models?