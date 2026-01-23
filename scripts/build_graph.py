from pathlib import Path
import pandas as pd
import networkx as nx

IN_CSV = Path("kg/triples_rebel.csv")
OUT_GRAPH = Path("kg/graph.graphml")

def main():
    df = pd.read_csv(IN_CSV)
    G = nx.DiGraph()

    for _, row in df.iterrows():
        s, r, o = str(row["subject"]), str(row["relation"]), str(row["object"])
        G.add_node(s)
        G.add_node(o)
        G.add_edge(s, o, relation=r, source=row.get("source", ""), page=row.get("page", ""))

    nx.write_graphml(G, OUT_GRAPH)
    print(f"Nodes={G.number_of_nodes()} Edges={G.number_of_edges()}")
    print(f"Saved: {OUT_GRAPH}")

if __name__ == "__main__":
    main()
