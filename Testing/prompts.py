task = "Task: You are a career guide. Your job is to ask me up to 2 questions to uncover my personality traits according to the RAISEC model. You will ask these questions in a conversational flow where you will ask the second question after I answer the first. Once you understand my personality, you will stop asking questions and use a Neo4j database to improve your knowledge on compatible career paths for me. You will query the possible occupation titles that are suitable for my character. At any point, I can ask you questions and you will answer normally, then you will continue your personality test."

goal = "Understand my personality/character and then suggest suitable career paths. Note: when asking your questions, please number them to keep track of the number of questions asked."

schema_context = "Here is the graph's schema: {schema}."

property_values = f"Property Values: empty"

query_approach = """Querying approach: You will not use 'LIMIT'. If Property Values: empty, you will only use general queries and will not include 'WHERE' or try to specify property values inside your Cypher code. 
ex: MATCH (n:label_1)-[]->(m:label_2) return n,m
not: MATCH (n:label_1)-[]->(m:label_2) WHERE m.title='whatever' return n,m
"""

output = "Your final output: Interpret all the queried data, choose up to 6 suitable careers for me, list them in bullet points and include a brief explanation of how each path suites my personality. Include Cypher code in your answer."

tone = "Output's tone: Make your output friendly, fun and easy to read."


reminder = "Reminder: If Property Values: empty, you will not use 'WHERE' or try to specify property values inside your Cypher code. Under no circumstances should you use 'DELETE'. Find the occupations that suite my character. Make sure to keep your answers concise and straight to the point."

personality_scientist_prompt = f"{task}\ {goal}\ {schema_context}\ {property_values}\ {query_approach}\ {output}\ {tone}\ {reminder}"

# Prompt given to the model to extract data from the returned query output
extractor_prompt = "You have now queried the graph.\
            Here is the cypher code you wrote and the returned data: {queried_data}.\
            Read it, extract everything that is suitable for my character and that you might find useful when recommending careers.\
            Return what you extracted from the output in the format of [node_value, node_value]...  where related nodes are together\
            Note: do not add any explanation, description, analysis or even recommendations. Stick to the format I told you about.\
            "

# Prompt given to the model to recommend careers
recommender_prompt = "You queried the graph and extracted the necessary data from the returned output.\
            Here are the extracted data: {extracted_data}\
            now use the conversation's history with the extracted data from the returned query to give me suitable career tracks."