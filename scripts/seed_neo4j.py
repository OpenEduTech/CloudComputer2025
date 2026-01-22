import os
import time
from neo4j import GraphDatabase

# Neo4j Connection Configuration
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "1234567888"))

# Mock Data to be inserted (Matching frontend/src/mockGraphData.js structure)
NODES = [
    {
        "id": "Deep Learning",
        "label": "Deep Learning",
        "group": "Concept",
        "size": 60,
        "confidence": 1.0,
        "source_type": "textbook",
        "source": "Deep Learning (Goodfellow et al.)",
        "url": "",
        "info": "A subset of machine learning based on artificial neural networks with representation learning."
    },
    {
        "id": "Transformer",
        "label": "Transformer",
        "group": "Architecture",
        "size": 45,
        "confidence": 0.98,
        "source_type": "paper",
        "source": "Attention Is All You Need (2017)",
        "url": "https://arxiv.org/abs/1706.03762",
        "info": "A model architecture eschewing recurrence and instead relying entirely on an attention mechanism."
    },
    {
        "id": "BERT",
        "label": "BERT",
        "group": "Architecture",
        "size": 40,
        "confidence": 0.95,
        "source_type": "paper",
        "source": "BERT: Pre-training of Deep Bidirectional Transformers",
        "url": "https://arxiv.org/abs/1810.04805",
        "info": "Bidirectional Encoder Representations from Transformers."
    },
    {
        "id": "GPT-3",
        "label": "GPT-3",
        "group": "Architecture",
        "size": 42,
        "confidence": 0.92,
        "source_type": "paper",
        "source": "Language Models are Few-Shot Learners",
        "url": "https://arxiv.org/abs/2005.14165",
        "info": "A state-of-the-art language model with 175 billion parameters."
    },
    {
        "id": "ResNet",
        "label": "ResNet",
        "group": "Architecture",
        "size": 35,
        "confidence": 0.88,
        "source_type": "paper",
        "source": "Deep Residual Learning for Image Recognition",
        "url": "https://arxiv.org/abs/1512.03385",
        "info": "Introduced residual connections to allow training of very deep networks."
    },
    {
        "id": "LSTM",
        "label": "LSTM",
        "group": "Architecture",
        "size": 30,
        "confidence": 0.85,
        "source_type": "textbook",
        "source": "Deep Learning (Goodfellow et al.)",
        "url": "",
        "info": "Long Short-Term Memory networks are a special kind of RNN."
    },
    {
        "id": "CNN",
        "label": "CNN",
        "group": "Architecture",
        "size": 38,
        "confidence": 0.90,
        "source_type": "textbook",
        "source": "Deep Learning (Goodfellow et al.)",
        "url": "",
        "info": "Convolutional Neural Networks, specialized for processing grid-like data."
    },
    {
        "id": "Adam",
        "label": "Adam",
        "group": "Optimization",
        "size": 25,
        "confidence": 0.94,
        "source_type": "paper",
        "source": "Adam: A Method for Stochastic Optimization",
        "url": "https://arxiv.org/abs/1412.6980",
        "info": "An algorithm for first-order gradient-based optimization."
    },
    {
        "id": "SGD",
        "label": "SGD",
        "group": "Optimization",
        "size": 28,
        "confidence": 0.96,
        "source_type": "textbook",
        "source": "Deep Learning (Goodfellow et al.)",
        "url": "",
        "info": "Stochastic Gradient Descent, the backbone of training neural networks."
    },
    {
        "id": "Backprop",
        "label": "Backpropagation",
        "group": "Optimization",
        "size": 35,
        "confidence": 0.99,
        "source_type": "textbook",
        "source": "Pattern Recognition and Machine Learning (Bishop)",
        "url": "",
        "info": "The primary algorithm for computing gradients in neural networks."
    },
    {
        "id": "GPU",
        "label": "GPU",
        "group": "Hardware",
        "size": 32,
        "confidence": 0.91,
        "source_type": "textbook",
        "source": "Computer Architecture: A Quantitative Approach",
        "url": "",
        "info": "Graphics Processing Unit, essential for parallel processing."
    },
    {
        "id": "Attention",
        "label": "Attention Mechanism",
        "group": "Architecture",
        "size": 36,
        "confidence": 0.93,
        "source_type": "paper",
        "source": "Neural Machine Translation by Jointly Learning to Align and Translate",
        "url": "https://arxiv.org/abs/1409.0473",
        "info": "Allows the model to focus on different parts of the input sequence."
    },
    # --- New Data for Depth Testing ---
    {
        "id": "Self-Attention",
        "label": "Self-Attention",
        "group": "Mechanism",
        "size": 30,
        "confidence": 0.95,
        "source_type": "paper",
        "source": "Attention Is All You Need",
        "url": "",
        "info": "Mechanism relating different positions of a single sequence in order to compute a representation of the sequence."
    },
    {
        "id": "Multi-Head Attention",
        "label": "Multi-Head Attention",
        "group": "Mechanism",
        "size": 32,
        "confidence": 0.96,
        "source_type": "paper",
        "source": "Attention Is All You Need",
        "url": "",
        "info": "Runs through the attention mechanism several times in parallel."
    },
    {
        "id": "Encoder",
        "label": "Encoder",
        "group": "Component",
        "size": 28,
        "confidence": 0.90,
        "source_type": "textbook",
        "source": "Deep Learning Systems",
        "url": "",
        "info": "Component that processes the input."
    },
    {
        "id": "Decoder",
        "label": "Decoder",
        "group": "Component",
        "size": 28,
        "confidence": 0.90,
        "source_type": "textbook",
        "source": "Deep Learning Systems",
        "url": "",
        "info": "Component that generates the output."
    },
    {
        "id": "Feed Forward",
        "label": "Feed Forward Network",
        "group": "Component",
        "size": 25,
        "confidence": 0.88,
        "source_type": "textbook",
        "source": "Neural Networks 101",
        "url": "",
        "info": "Simple neural network layer."
    },
    {
        "id": "Layer Norm",
        "label": "Layer Normalization",
        "group": "Optimization",
        "size": 22,
        "confidence": 0.92,
        "source_type": "paper",
        "source": "Layer Normalization (2016)",
        "url": "https://arxiv.org/abs/1607.06450",
        "info": "Technique to normalize the activities of the neurons."
    },
    {
        "id": "ViT",
        "label": "Vision Transformer (ViT)",
        "group": "Architecture",
        "size": 38,
        "confidence": 0.94,
        "source_type": "paper",
        "source": "An Image is Worth 16x16 Words",
        "url": "https://arxiv.org/abs/2010.11929",
        "info": "Applying Transformers directly to images."
    },
    {
        "id": "Swin Transformer",
        "label": "Swin Transformer",
        "group": "Architecture",
        "size": 35,
        "confidence": 0.91,
        "source_type": "paper",
        "source": "Swin Transformer: Hierarchical Vision Transformer using Shifted Windows",
        "url": "https://arxiv.org/abs/2103.14030",
        "info": "A hierarchical Transformer whose representation is computed with shifted windows."
    }
]

RELATIONSHIPS = [
    ("Transformer", "Attention", "USES", "Transformer utilizes self-attention layers."),
    ("BERT", "Transformer", "EVOLVED_FROM", "BERT is based on the Transformer architecture."),
    ("GPT-3", "Transformer", "EVOLVED_FROM", "GPT models utilize the Transformer decoder stack."),
    ("Transformer", "LSTM", "REPLACES", "Transformers largely replaced RNN/LSTMs in NLP."),
    ("ResNet", "CNN", "EVOLVED_FROM", "ResNet is a specific type of CNN."),
    ("Adam", "SGD", "EVOLVED_FROM", "Adam combines ideas from RMSProp and Momentum."),
    ("CNN", "GPU", "ACCELERATED_BY", "CNN training is highly efficient on GPUs."),
    ("Transformer", "GPU", "ACCELERATED_BY", "Training transformers requires massive GPU compute."),
    ("LSTM", "Backprop", "TRAINED_WITH", "LSTMs are trained using Backpropagation Through Time."),
    ("CNN", "Backprop", "TRAINED_WITH", "Standard training method for CNNs."),
    ("Transformer", "Adam", "OPTIMIZED_BY", "Adam is the standard optimizer for Transformers."),
    ("Deep Learning", "Transformer", "INCLUDES", "Core architecture in DL."),
    ("Deep Learning", "CNN", "INCLUDES", "Core architecture in DL."),
    ("Deep Learning", "Backprop", "DEPENDS_ON", "Fundamental training algorithm."),
    
    # --- New Relationships for Depth Testing ---
    # Depth 1 from Transformer -> Attention
    ("Attention", "Self-Attention", "IS_A", "Self-attention is a specific type of attention."),
    
    # Depth 2 from Transformer -> Self-Attention -> Multi-Head Attention
    ("Self-Attention", "Multi-Head Attention", "PART_OF", "Multi-head attention consists of multiple self-attention heads."),
    
    # Transformer Internal Structure
    ("Transformer", "Encoder", "HAS_COMPONENT", "Original Transformer has an Encoder stack."),
    ("Transformer", "Decoder", "HAS_COMPONENT", "Original Transformer has a Decoder stack."),
    
    # Depth 3: Transformer -> Encoder -> Feed Forward
    ("Encoder", "Feed Forward", "CONTAINS", "Each encoder layer contains a feed forward network."),
    ("Encoder", "Self-Attention", "CONTAINS", "Each encoder layer contains a self-attention mechanism."),
    
    # Depth 3/4: Transformer -> Encoder -> Layer Norm
    ("Encoder", "Layer Norm", "USES", "Each sub-layer is followed by layer normalization."),
    
    # Evolution Chain (Depth Testing)
    # Deep Learning -> Transformer -> ViT -> Swin Transformer
    ("ViT", "Transformer", "ADAPTS", "ViT adapts Transformer for computer vision."),
    ("Swin Transformer", "ViT", "IMPROVES", "Swin improves upon ViT with hierarchical windows.")
]

def seed_data(tx):
    print("Clearing existing data...")
    tx.run("MATCH (n) DETACH DELETE n")

    print("Creating nodes...")
    for node in NODES:
        query = """
        CREATE (n:Entity {
            id: $id,
            label: $label,
            group: $group,
            size: $size,
            confidence: $confidence,
            source_type: $source_type,
            source: $source,
            url: $url,
            info: $info
        })
        """
        tx.run(query, **node)

    print("Creating relationships...")
    for source, target, rel_type, desc in RELATIONSHIPS:
        query = f"""
        MATCH (a:Entity {{id: $source}}), (b:Entity {{id: $target}})
        MERGE (a)-[r:{rel_type} {{desc: $desc, relation: $rel_type}}]->(b)
        """
        tx.run(query, source=source, target=target, rel_type=rel_type, desc=desc)

def main():
    print(f"Connecting to Neo4j at {URI}...")
    # Retry logic for waiting Neo4j to start
    max_retries = 30
    driver = None
    
    for i in range(max_retries):
        try:
            driver = GraphDatabase.driver(URI, auth=AUTH)
            driver.verify_connectivity()
            print("Connected to Neo4j!")
            break
        except Exception as e:
            print(f"Connection failed ({i+1}/{max_retries}): {e}")
            time.sleep(2)
    
    if not driver:
        print("Could not connect to Neo4j after retries.")
        return

    with driver.session() as session:
        session.execute_write(seed_data)
        print("Data seeding completed successfully!")
    
    driver.close()

if __name__ == "__main__":
    main()
