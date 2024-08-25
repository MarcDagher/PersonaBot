from neo4j import GraphDatabase
import ast

def connect_to_database(uri, username, password):
  driver = GraphDatabase.driver(uri=uri, auth=(username, password))
  return driver


def create_node(driver, label, properties=""):
    """
    Create a node that can have one or more properties.
    
    driver: Neo4j driver instance
    label: Label for the node (ex: Occupation)
    properties: Dictionary of properties for a node (ex: {'title': 'Psychologist', degree_type: 'BS' ... })
    """
    with driver.session() as session:  
      # Format property dictionaries in a format that suites Cypher strings
      property_keys = ", ".join([f"{key}: ${key}" for key in properties.keys()]) # ex: {title: $title}
      set_clause = ", ".join([f"n.{key} = ${key}" for key in properties.keys()]) # ex: n.title = $title
      
      # Construct query
      query = f"""
      MERGE (n:{label} {{{property_keys}}})
      ON CREATE SET {set_clause}
      """
      
      # Execute query
      session.run(query, properties)

def create_relation(driver, n_label_1, n_identifier_1, n_label_2, n_identifier_2, relation_label, relation_properties={"properties":"{}"}):
  """
  Create a realtion between two nodes. ##NOTE n_label_1 points to n_label_2 NOTE##

  driver: instance of Neo4j driver.
  n_label_1: label for the first node. (ex: Occupation)
  n_identifier_1: dictionary of property {key:values} to specify the node we are searching for. (ex: {'title': 'Psychologist'})

  n_label_2: label for the second node. (ex: Basic_Skill)
  n_identifier_2: dictionary of property {key:values} to specify the node we are searching for. (ex: {'level': 20})

  relation_label: label given to the relationship between the two nodes. ex: ( ()-[r:'is_needed_by']->() )
  relation_label: properties given to the relationship between two nodes. ex: ( ()-[r:label {'level': 'High'}]->() )
  """
  
  # Format property dictionaries in a format that suites Cypher strings
  properties_1 = ", ".join([f"""{item[0]}: "{item[1]}" """ for item in n_identifier_1.items()]) # ex: {title: 'Singer'}
  properties_2 = ", ".join([f""" {item[0]}: "{item[1]}" """ for item in n_identifier_2.items()]) # ex: {title: 'Singing'}
  properties_3 = ", ".join([f""" {item[0]}: "{item[1]}" """ for item in relation_properties.items()]) # ex: {level: 20}

  # Construct query
  query = f"""
  MATCH (n:{n_label_1} {{{properties_1}}})
  MATCH (m:{n_label_2} {{{properties_2}}})
  MERGE (n)-[r:{relation_label} {{{properties_3}}}]->(m)
  """

  with driver.session() as session:
    session.run(query)

def populate_graph(driver, dataset):
  for i in range(len(dataset)):
    node_1 = ast.literal_eval(dataset.loc[i, 'Node_1'])
    node_2 = ast.literal_eval(dataset.loc[i, 'Node_2'])
    relation = ast.literal_eval(dataset.loc[i, 'Relation'])

    create_node(
      driver=driver,
      label=f"`{node_1['label']}`",
      properties=ast.literal_eval(node_1['properties'])
    )

    create_node(
      driver=driver,
      label=f"`{node_2['label']}`",
      properties=ast.literal_eval(node_2['properties'])
    )
    
    create_relation(
      driver=driver,
      n_identifier_1=ast.literal_eval(node_1['identifier']), n_label_1=f"`{node_1['label']}`", 
      n_identifier_2=ast.literal_eval(node_2['identifier']), n_label_2=f"`{node_2['label']}`",
      relation_label=relation['label'], relation_properties=ast.literal_eval(relation['properties'])
    )