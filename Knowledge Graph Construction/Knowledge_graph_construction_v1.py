# Shows good relationship and entities extraction however the output is not in the correct format as some nodes are of mixed names insted of one word
# example: There's a node of name easygoingcareless instead of easygoing and careless as two separate nodes
# Also, the output is not deduplicated as there are multiple instances of similar relationships connected same nodes
# Needs to get processed further in terms of speed and accuracy as it takes time to process and some entities classifications are not correct and some relationships are general "isRelatedTo"

import os
import time
import PyPDF2
from xml.dom.minidom import Document
from bs4 import BeautifulSoup
from groq import InternalServerError
import re, csv
from typing import List, Set, Dict, Tuple

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from py2neo import Graph, Node, Relationship as Neo4jRelationship
from dotenv import load_dotenv

# Download necessary NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

lemmatizer = WordNetLemmatizer()

class Entity(BaseModel):
    name: str = Field(description="Name of the entity")
    type: str = Field(description="Type of the entity (e.g., PersonalityTrait, Job, Skill)")

class RelationshipModel(BaseModel):
    subject: str = Field(description="Subject entity of the relationship")
    predicate: str = Field(description="Predicate describing the relationship")
    object: str = Field(description="Object entity of the relationship")

class KnowledgeGraphOutput(BaseModel):
    entities: List[Entity] = Field(description="List of entities extracted from the text")
    relationships: List[RelationshipModel] = Field(description="List of relationships extracted from the text")

def extract_text_from_file(file_path):
    _, file_extension = os.path.splitext(file_path.lower())
    
    if file_extension == '.csv':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            csv_reader = csv.reader(file)
            return '\n'.join([','.join(row) for row in csv_reader])
    elif file_extension in ['.txt']:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    elif file_extension in ['.html', '.htm']:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            soup = BeautifulSoup(file, 'html.parser')
            return soup.get_text()
    elif file_extension == '.pdf':
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            return ' '.join(page.extract_text() for page in reader.pages)
    elif file_extension in ['.docx', '.doc']:
        doc = Document(file_path)
        return ' '.join(paragraph.text for paragraph in doc.paragraphs)
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

def process_csv_data(text):
    entities = []
    relationships = []
    
    rows = [row.split(',') for row in text.split('\n') if row.strip()]
    headers = rows[0]
    
    for row in rows[1:]:
        if len(row) != len(headers):
            continue  # Skip malformed rows
        
        occupation = Entity(name=clean_entity_name(row[-1]), type='Job')
        entities.append(occupation)
        
        for i, value in enumerate(row[:-1]):
            attr_name = clean_entity_name(f"{headers[i]}_{value}")
            attr_entity = Entity(name=attr_name, type=headers[i])
            entities.append(attr_entity)
            
            relationship = RelationshipModel(
                subject=occupation.name,
                predicate=f"has_{headers[i].lower().replace(' ', '_')}",
                object=attr_name
            )
            relationships.append(relationship)
    
    return entities, relationships

def traverse_folder(folder_path):
    extracted_texts = []
    if not os.path.exists(folder_path):
        print(f"Error: The folder path '{folder_path}' does not exist.")
        return extracted_texts

    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                text = extract_text_from_file(file_path)
                extracted_texts.append((file, text))
            except Exception as e:
                print(f"Error processing {file}: {str(e)}")
    
    if not extracted_texts:
        print("No files were successfully processed.")
    else:
        print(f"Successfully processed {len(extracted_texts)} files.")
    
    return extracted_texts

def clean_text(text):
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def preprocess_text(text):
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words]
    return ' '.join(tokens)

def clean_and_preprocess(text):
    cleaned_text = clean_text(text)
    preprocessed_text = preprocess_text(cleaned_text)
    return preprocessed_text

def clean_entity_name(name: str) -> str:
    return ''.join(word.capitalize() for word in name.split())

output_parser = PydanticOutputParser(pydantic_object=KnowledgeGraphOutput)

prompt_template = PromptTemplate(
    template="""
    Extract entities and relationships from the following text to construct a knowledge graph focused on the topic of {topic}:
    
    {text}
    
    Only extract information relevant to {topic}. Focus on key concepts, traits, jobs, and their relationships within the context of {topic}.
    
    Important: Ensure that all entity and relationship names contain no spaces. Use CamelCase or PascalCase for multi-word names.
    
    {format_instructions}
    
    Provide the output in the specified JSON format.
    """,
    input_variables=["text", "topic"],
    partial_variables={"format_instructions": output_parser.get_format_instructions()}
)

def clean_llm_output(output: str) -> str:
    output = re.sub(r'(\w+)\1{2,}', r'\1', output)
    match = re.search(r'\{.*\}', output, re.DOTALL)
    if match:
        return match.group(0)
    return output

def extract_entities_relationships_fallback(text: str) -> Tuple[List[Entity], List[RelationshipModel]]:
    entities = []
    relationships = []
    
    entity_matches = re.findall(r'"name":\s*"([^"]+)",\s*"type":\s*"([^"]+)"', text)
    for name, type in entity_matches:
        entities.append(Entity(name=name, type=type))
    
    relationship_matches = re.findall(r'"subject":\s*"([^"]+)",\s*"predicate":\s*"([^"]+)",\s*"object":\s*"([^"]+)"', text)
    for subject, predicate, obj in relationship_matches:
        relationships.append(RelationshipModel(subject=subject, predicate=predicate, object=obj))
    
    return entities, relationships

def extract_kg_elements(text, topic, max_retries=3, delay=5):
    # Check if the text is CSV data
    if text.count('\n') > 0 and ',' in text.split('\n')[0]:
        return process_csv_data(text)
    
    llm = ChatGroq(temperature=0, model_name="llama-3.1-70b-versatile")
    
    chain = LLMChain(llm=llm, prompt=prompt_template)
    
    for attempt in range(max_retries):
        try:
            result = chain.run(text=text, topic=topic)
            cleaned_result = clean_llm_output(result)
            try:
                parsed_output = output_parser.parse(cleaned_result)
                return parsed_output.entities, parsed_output.relationships
            except Exception as e:
                print(f"Error parsing output: {e}")
                print("Attempting fallback extraction method...")
                return extract_entities_relationships_fallback(cleaned_result)
        except InternalServerError as e:
            if attempt < max_retries - 1:
                print(f"Encountered error: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"Max retries reached. Error: {e}")
                return [], []
        except Exception as e:
            print(f"Unexpected error: {e}")
            return [], []

def lemmatize_entity_name(name: str) -> str:
    words = name.lower().split()
    lemmatized_words = [lemmatizer.lemmatize(word) for word in words]
    return "".join(word.capitalize() for word in lemmatized_words)

def deduplicate_entities(entities: List[Entity]) -> List[Entity]:
    unique_entities: Dict[Tuple[str, str], Entity] = {}
    for entity in entities:
        key = (lemmatize_entity_name(entity.name), entity.type.lower())
        if key not in unique_entities:
            unique_entities[key] = entity
        else:
            # If the entity already exists, keep the one with the shorter name
            if len(entity.name) < len(unique_entities[key].name):
                unique_entities[key] = entity
    return list(unique_entities.values())

def deduplicate_relationships(relationships: List[RelationshipModel], entities: Set[str]) -> List[RelationshipModel]:
    unique_relationships = set()
    deduplicated_relationships = []
    for rel in relationships:
        subject = lemmatize_entity_name(rel.subject)
        object = lemmatize_entity_name(rel.object)
        if subject in entities and object in entities:
            key = (subject, rel.predicate.lower(), object)
            if key not in unique_relationships:
                unique_relationships.add(key)
                deduplicated_relationships.append(RelationshipModel(subject=subject, predicate=rel.predicate, object=object))
    return deduplicated_relationships

def clear_database(graph: Graph):
    graph.delete_all()
    print("Database cleared: All nodes and relationships have been deleted.")

def remove_relationshipless_nodes(graph: Graph):
    query = """
    MATCH (n)
    WHERE NOT (n)--()
    DELETE n
    """
    graph.run(query)
    print("Removed nodes without relationships.")

def create_knowledge_graph(entities: List[Entity], relationships: List[RelationshipModel], neo4j_uri: str, neo4j_user: str, neo4j_password: str):
    graph = Graph(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    # Clear the database before creating new nodes and relationships
    clear_database(graph)
    
    deduplicated_entities = deduplicate_entities(entities)
    
    entity_names = {lemmatize_entity_name(entity.name) for entity in deduplicated_entities}
    
    deduplicated_relationships = deduplicate_relationships(relationships, entity_names)
    
    nodes = {}
    for entity in deduplicated_entities:
        lemmatized_name = lemmatize_entity_name(entity.name)
        # Check if the node already exists
        existing_node = graph.nodes.match(entity.type, name=lemmatized_name).first()
        if existing_node:
            node = existing_node
        else:
            node = Node(entity.type, name=lemmatized_name)
            graph.create(node)
        nodes[lemmatized_name] = node
    
    relationships_created = 0
    for rel in deduplicated_relationships:
        subject_node = nodes.get(lemmatize_entity_name(rel.subject))
        object_node = nodes.get(lemmatize_entity_name(rel.object))
        if subject_node and object_node:
            # Check if the relationship already exists
            existing_rel = graph.match((subject_node, object_node), r_type=rel.predicate).first()
            if not existing_rel:
                relationship = Neo4jRelationship(subject_node, rel.predicate, object_node)
                graph.create(relationship)
                relationships_created += 1

    # Remove nodes without relationships
    remove_relationshipless_nodes(graph)
    
    print(f"Created {len(nodes)} nodes and {relationships_created} relationships in Neo4j.")
    print("Removed nodes without relationships.")

def construction():
    load_dotenv()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY is not set in the environment variables.")
        return

    folder_path = r'C:\Users\Nagham\OneDrive\Desktop\Nagham\Self Learning\ZAKA\Capstone Project\Llama3.1 Project\knowledge_docs'
    print(f"Attempting to process files in: {folder_path}")
    
    extracted_data = traverse_folder(folder_path)
    if not extracted_data:
        print("Error: No data was extracted from the files.")
        return
    
    cleaned_data = [(file, clean_and_preprocess(text)) for file, text in extracted_data]
    print(f"Cleaned and preprocessed {len(cleaned_data)} files.")
    
    topic = "RIASEC Personality Traits and Job Recommendations"
    all_entities = []
    all_relationships = []
    
    for file, text in cleaned_data:
        print(f"Processing file: {file}")
        entities, relationships = extract_kg_elements(text, topic)
        if entities or relationships:
            all_entities.extend(entities)
            all_relationships.extend(relationships)
        else:
            print(f"No entities or relationships extracted from {file}")
    
    print(f'Total entities extracted (before deduplication): {len(all_entities)}')
    print(f'Total relationships extracted (before deduplication): {len(all_relationships)}')
    
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not all([neo4j_uri, neo4j_user, neo4j_password]):
        print("Error: Neo4j connection details are not fully specified in the environment variables.")
        return
    
    print("Attempting to create deduplicated knowledge graph in Neo4j...")
    create_knowledge_graph(all_entities, all_relationships, neo4j_uri, neo4j_user, neo4j_password)

if __name__ == "__main__":
    construction()