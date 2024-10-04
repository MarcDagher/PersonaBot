import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

def display_error_box(text):
   st.markdown(f"""
                <p style="font-size: 14px; background-color: #f95353; color: white; text-align: center; border-radius: 5px; padding: 10px 0">
                    {text}
                </p>
              """, unsafe_allow_html=True)

def display_knowledge_graph(data):
    head = []
    tail = []

    # Extract head and tail nodes
    for i in range(len(data)):
        row = data[i]
        keys = list(row.keys())
        node_1 = row[keys[0]]['title']
        node_2 = row[keys[1]]['title']

        head.append(node_1)
        tail.append(node_2)

    # Create a DataFrame
    df = pd.DataFrame({'head': head, 'tail': tail})

    # Create the graph
    G = nx.Graph()
    for _, row in df.iterrows():
        G.add_edge(row['head'], row['tail'], label="")

    # Get positions for nodes
    pos = nx.fruchterman_reingold_layout(G, k=0.7)

    # Create edge traces (lines between nodes)
    edge_traces = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=0.3, color='gray'),
            hoverinfo='none'
        )
        edge_traces.append(edge_trace)

    # Assign colors based on whether the node is in the head or tail
    node_colors = []
    for node in G.nodes():
        if node in head:
            node_colors.append('lightblue')  # Color for head nodes (node_1)
        elif node in tail:
            node_colors.append('lightcoral')   # Color for tail nodes (node_2)
        else:
            node_colors.append('gold')  # Default color

    # Create node trace (nodes with their respective colors)
    node_trace = go.Scatter(
        x=[pos[node][0] for node in G.nodes()],
        y=[pos[node][1] for node in G.nodes()],
        mode='markers+text',
        marker=dict(size=10, color=node_colors),  # Use node_colors list for colors
        text=[node for node in G.nodes()],
        textposition='top center',
        hoverinfo='text',
        textfont=dict(size=7)
    )

    # Create edge label trace (optional, for labeling edges)
    edge_label_trace = go.Scatter(
        x=[(pos[edge[0]][0] + pos[edge[1]][0]) / 2 for edge in G.edges()],
        y=[(pos[edge[0]][1] + pos[edge[1]][1]) / 2 for edge in G.edges()],
        mode='text',
        text=[G[edge[0]][edge[1]]['label'] for edge in G.edges()],
        textposition='middle center',
        hoverinfo='none',
        textfont=dict(size=7)
    )

    # Create layout
    layout = go.Layout(
        title='',
        titlefont_size=16,
        title_x=0.5,
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis_visible=False,
        yaxis_visible=False
    )

    # Create Plotly figure
    fig = go.Figure(data=edge_traces + [node_trace, edge_label_trace], layout=layout)

    return fig


def display_extracted_traits_data(data):
    heads = []
    tails = []
    relations = []

    # Extract heads, tails, and relations
    for row in data:
        if len(row) == 3:
            head = row[0]
            relation = row[1]
            tail = row[2]
        else:
            head = row[0]
            relation = " "
            tail = row[1]

        heads.append(head)
        tails.append(tail)
        relations.append(relation)

    # Create a DataFrame
    df = pd.DataFrame({'head': heads, 'tail': tails, 'relation': relations})

    # Create the graph
    G = nx.Graph()
    for _, row in df.iterrows():
        # G.add_edge(row['head'], row['tail'], label=row['relation'])
        G.add_edge(row['head'], row['tail'], label="")

    # Get positions for nodes
    pos = nx.fruchterman_reingold_layout(G, k=1.0)

    # Assign colors based on whether the node is in the heads or tails
    node_colors = []
    for node in G.nodes():
        if node in heads:
            node_colors.append('lightblue')  # Color for head nodes
        elif node in tails:
            node_colors.append('lightcoral')   # Color for tail nodes
        else:
            node_colors.append('gold')  # Default color

    # Create edge traces
    edge_traces = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=0.3, color='slategray'),
            hoverinfo='none'
        )
        edge_traces.append(edge_trace)

    # Create node trace
    node_trace = go.Scatter(
        x=[pos[node][0] for node in G.nodes()],
        y=[pos[node][1] for node in G.nodes()],
        mode='markers+text',
        marker=dict(size=10, color=node_colors),  # Use node_colors list for colors
        text=[node for node in G.nodes()],
        textposition='top center',
        hoverinfo='text',
        textfont=dict(size=7)
    )

    # Create edge label trace
    edge_label_trace = go.Scatter(
        x=[(pos[edge[0]][0] + pos[edge[1]][0]) / 2 for edge in G.edges()],
        y=[(pos[edge[0]][1] + pos[edge[1]][1]) / 2 for edge in G.edges()],
        mode='text',
        text=[G[edge[0]][edge[1]]['label'] for edge in G.edges()],
        textposition='middle center',
        hoverinfo='none',
        textfont=dict(size=7)
    )

    # Create layout
    layout = go.Layout(
        title='',
        titlefont_size=16,
        title_x=0.5,
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis_visible=False,
        yaxis_visible=False
    )

    # Create Plotly figure
    fig = go.Figure(data=edge_traces + [node_trace, edge_label_trace], layout=layout)

    return fig