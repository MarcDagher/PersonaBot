from neo4j import GraphDatabase
import re
import ast

def connect_to_database(uri, username, password):
  driver = GraphDatabase.driver(uri=uri, auth=(username, password))
  return driver

##

def preprocess_string(text):
  text = re.sub(r"[ -]", "_", text)
  return text

##

def create_node(driver, label, properties):
    """
    Create a node that can have one or more properties.
    
    driver: Neo4j driver instance
    label: Label for the node (example: Occupation)
    properties: Dictionary of properties for a node (example: {'title': 'Psychologist', degree_type: 'BS' ... })

    NOTE: properties is required and can not be an empty dictionary
    """
    with driver.session() as session:  
      # Format property dictionaries in a format that suites Cypher strings
      property_keys = ", ".join([f"{key}: ${key}" for key in properties.keys()]) # example: {title: $title}
      set_clause = ", ".join([f"n.{key} = ${key}" for key in properties.keys()]) # example: n.title = $title
      
      # Remove trailing white spaces and replace [white spaces, "-"] between words with "_"
      label = preprocess_string(label.strip())

      # Construct query
      query = f"""
      MERGE (n:{label} {{{property_keys}}})
      ON CREATE SET {set_clause}
      """
      
      # Execute query
      session.run(query, properties)

##

def create_relation(driver, n_label_1, n_identifier_1, n_label_2, n_identifier_2, relation_label, relation_properties={}):
  """
  Create a reltion between two nodes. NOTE: n_label_1 -[points to]-> n_label_2

  driver: instance of Neo4j driver.

  n_label_1: label for the first node. (example: Occupation)
  n_identifier_1: dictionary of properties {key:values} to specify the node we are searching for. (example: {'title': 'Psychologist'})

  n_label_2: label for the second node. (example: Basic_Skill)
  n_identifier_2: dictionary of properties {key:values} to specify the node we are searching for. (example: {'level': 20})

  relation_label: label given to the relationship of the two nodes. example: ( ()-[r:'is_needed_by']->() )
  relation_label: properties given to the relationship of the two nodes. example: ( ()-[r:relation_label {'level': 'High'}]->() )
  
  NOTE: no values can be missing or set to empty dictionaries except for "relationship_properties"
  """
  
  # Format property dictionaries in a format that suites Cypher strings
  identifier_1 = ", ".join([f"""{item[0]}: "{item[1]}" """ for item in n_identifier_1.items()]) # example outcome: {title: 'Singer'}
  identifier_2 = ", ".join([f""" {item[0]}: "{item[1]}" """ for item in n_identifier_2.items()]) # example outcome: {title: 'Singing'}
  properties = ", ".join([f""" {item[0]}: "{item[1]}" """ for item in relation_properties.items()]) # example outcome: {level: 20}

  # Remove trailing white spaces and replace [white spaces, "-"] between words with "_"
  n_label_1 = preprocess_string(n_label_1.strip())
  n_label_2 = preprocess_string(n_label_2.strip())
  relation_label = preprocess_string(relation_label.strip())

  # Construct query
  query = f"""
  MATCH (n:{n_label_1} {{{identifier_1}}})
  MATCH (m:{n_label_2} {{{identifier_2}}})
  MERGE (n)-[r:{relation_label} {{{properties}}}]->(m)
  """

  with driver.session() as session:
    session.run(query)

##

def populate_graph(driver, dataset):
  """
  In this function, the dataset is loaded and each Node's label and properties are extracted.
  The three functions created above are used to then create a relation between the two nodes.
  """
  for i in range(len(dataset)):
    node_1 = ast.literal_eval(dataset.loc[i, 'Node_1'])
    node_2 = ast.literal_eval(dataset.loc[i, 'Node_2'])
    relation = ast.literal_eval(dataset.loc[i, 'Relation'])

    create_node(
      driver=driver,
      label=f"{node_1['label']}",
      properties=ast.literal_eval(node_1['properties'])
    )

    create_node(
      driver=driver,
      label=f"{node_2['label']}",
      properties=ast.literal_eval(node_2['properties'])
    )
    
    if "properties" in relation.keys():
      create_relation(
        driver=driver,
        n_identifier_1=ast.literal_eval(node_1['identifier']), n_label_1=f"{node_1['label']}", 
        n_identifier_2=ast.literal_eval(node_2['identifier']), n_label_2=f"{node_2['label']}",
        relation_label=relation['label'], relation_properties=ast.literal_eval(relation['properties'])
      )
    
    else:
      create_relation(
        driver=driver,
        n_identifier_1=ast.literal_eval(node_1['identifier']), n_label_1=f"{node_1['label']}", 
        n_identifier_2=ast.literal_eval(node_2['identifier']), n_label_2=f"{node_2['label']}",
        relation_label=relation['label']
      )