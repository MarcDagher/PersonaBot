<h1 align="center"> 🎓PersonaBot: A Retrieval-Augmented Agentic Career Guide</h1>

**PersonaBot** is an AI tool designed to help with career decision-making. It assesses user personality and skills through interactive interviews and recommends suitable career paths using a comprehensive knowledge graph based on the RIASEC model.

<h3>🕸️Knowledge Graph</h3>
<p>To ensure accurate personality assessment and job recommendations, the system uses a <a href="https://neo4j.com/">Neo4j</a> knowledge graph based on the RIASEC personality model and the <a href="https://www.onetonline.org/find/descriptor/browse/1.C">O*NET dataset</a> to match user traits with suitable career paths. The system asks users a series of questions to analyze their personality traits and then queries a knowledge graph to suggest suitable occupations based on these traits. The key dataset used to create this knowledge graph is the O*NET Dataset, an extensive resource developed by the U.S. Department of Labor to provide detailed and comprehensive information about various occupations.</p>

To populate the knowledge graph with the extracted data from O*Net, we followed a specific <a href="https://github.com/MarcDagher/PersonaBot/blob/main/Knowledge_Graph/CSV_to_Knowledge_Graph/format_csvs.ipynb">CSV format</a>. The CSV format contains three columns: “Node_1,” “Node_2,” and “Relation.” Every node should have a “label,” “property,” and “identifier,” while every relation should have a “label” and optional “properties.” An example row in the CSV would look like this:
<li>Node_1: {'label': 'Occupation', 'properties': "{'title': 'Psychologist'}", 'identifier': "{'title': 'Psychologist'}"}</li>
<li>Node_2: {'label': 'Basic_Skill', 'properties': "{'title': 'Good Listener'}", 'identifier': "{'title': 'Good Listener'}"}</li>
<li>Relation: {'label': 'need_for_basic_skill', 'properties': "{'level': 'high'}"}</li> <br>
If you want to check out how we formatted our CSVs, go to this <a href="https://github.com/MarcDagher/PersonaBot/blob/main/Knowledge_Graph/CSV_to_Knowledge_Graph/create_graph_from_structured_data.ipynb">notebook</a>.
We created specific <a href="https://github.com/MarcDagher/PersonaBot/blob/main/Knowledge_Graph/CSV_to_Knowledge_Graph/graph_functions.py">graph functions</a> to add the data into the knowledge graph. If you want to use these functions, make sure to have a CSV file following this format.

<h3>🤖Agent</h3>

The system we built carries the following tasks:
<li>Conducts a personality test</li>
<li>Decides when to query the graph</li>
<li>Writes cypher code and queries the graph</li> 
<li>Extracts whatever it needs from the queried data</li> 
<li>Suggests suitable career tracks</li> 
<li>Answers any questions</li><br>
To orchestrate this <a href="https://github.com/MarcDagher/PersonaBot/blob/main/Images/agent.jpg">workflow</a> we used <a href="https://www.langchain.com/langgraph">LangGraph</a> and <a href="https://console.groq.com/docs/models">Groq</a>'s llama-3.1-70b-versatile for its tool-use capabilities.

<h3>⚙️Prompt Engineering</h3>

In designing prompts for the agent, we built each step in the workflow to match specific tasks and improve response accuracy. Since the system’s workflow contains multiple steps, we separated each of them into unique tasks with specific prompts. This approach led to smaller prompts, less tasks on an individual LLM, and fewer hallucinations throughout the system, resulting in more accurate results.

We explored prompting strategies like zero-shot and few-shot prompting but encountered inconsistencies and hallucinations from the LLMs, even with task separation and workload reduction. While example outputs improved format, they did not significantly enhance content, and few-shot prompting failed to deliver accurate results.

To address these issues, we developed structured task completion prompts inspired by chain-of-thought (CoT) prompting, which encourages coherent intermediate reasoning steps. By guiding the LLM through a step-by-step reasoning process, we achieved improved coherence and accuracy. This approach enabled the LLMs to generate more logical and relevant outputs, effectively adapting to user interactions.

You can check the prompts <a href="https://github.com/MarcDagher/PersonaBot/blob/main/Agent_App/FastAPI_Sub_Folder/Helpers/prompts.py">here</a>

<h3>📝LLM Evaluation</h3>

We generated <a href="https://github.com/MarcDagher/PersonaBot/blob/main/LLM_Evaluation/gpt_synthetic_data.csv">synthetic data</a> to evaluate the LLM's generation by simulating typical user-agent conversations with GPT-4o mini, creating a ground truth dataset formatted as a CSV file with three columns: conversation, extracted data, and output. This dataset was limited to 22 rows due to LLM rate limits and manually reviewed for applicability. <br>

We used <a href="https://docs.confident-ai.com/">DeepEval</a>, an evaluation framework for AI models, which supports multi-task evaluations and custom metrics. Our assessment metrics included:
<li>Answer Relevancy: Relevance of the output to the input</li>
<li>Faithfulness: Alignment of the output with the retrieval context</li>
<li>Logical Suggestions: Coherence of career suggestions based on user-agent conversations</li> <br>
The agent performed well, scoring 90-95% across all metrics. Additionally, we used LangSmith for continuous monitoring of the agent's workflows, which streamlined tracking, debugging, and optimizing AI models, ensuring consistent, high-quality outputs from the LLM.
<a href="https://github.com/MarcDagher/PersonaBot/blob/main/LLM_Evaluation/eval.ipynb">This</a> is the link to the evaluation notebook.

<h3>🎬Demo</h3>
In this demo, you will see the interaction with the conversational agent, as well as a visualization of the queried data from the knowledge graph and the data that the agent extracted from it. We built the app using FastAPI and Streamlit. <br><br>

![Demo](https://github.com/MarcDagher/PersonaBot/blob/main/Images_and_Videos/demo%20(1).gif)
