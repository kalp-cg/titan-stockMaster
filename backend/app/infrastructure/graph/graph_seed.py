"""Seed data for the economic knowledge graph.

Populates the in-memory graph with countries, commodities, sectors,
and companies along with their directional dependency weights.
"""

from __future__ import annotations

from app.domain.interfaces.knowledge_graph import GraphEdge, GraphNode, IKnowledgeGraph

# Macro nodes definition
MACRO_NODES = [
    # Countries & Regions
    ("usa", "country", "United States"),
    ("china", "country", "China"),
    ("india", "country", "India"),
    ("middle_east", "country", "Middle East"),
    ("russia", "country", "Russia"),
    ("australia", "country", "Australia"),
    ("germany", "country", "Germany"),

    # Commodities
    ("crude_oil", "commodity", "Crude Oil"),
    ("natural_gas", "commodity", "Natural Gas"),
    ("coal", "commodity", "Coal"),
    ("gold", "commodity", "Gold"),
    ("silver", "commodity", "Silver"),
    ("steel", "commodity", "Steel"),
    ("copper", "commodity", "Copper"),
    ("semiconductors", "commodity", "Semiconductors"),
    ("api_ingredients", "commodity", "Pharma APIs"),
    ("agricultural_products", "commodity", "Agri Products"),

    # Sectors
    ("technology", "sector", "Technology"),
    ("banking_finance", "sector", "Banking & Finance"),
    ("energy_utilities", "sector", "Energy & Utilities"),
    ("consumer_fmcg", "sector", "Consumer FMCG"),
    ("automobiles", "sector", "Automobiles"),
    ("metals_mining", "sector", "Metals & Mining"),
    ("defense_aerospace", "sector", "Defense & Aerospace"),
    ("aviation", "sector", "Aviation"),
    ("pharmaceuticals", "sector", "Pharmaceuticals"),
    ("infrastructure", "sector", "Infrastructure"),
    ("paints", "sector", "Paints"),
    ("cement", "sector", "Cement"),
    ("jewellery", "sector", "Jewellery & Retail"),
    
    # Influential Leaders & Speakers
    ("donald_trump", "person", "Donald Trump"),
    ("narendra_modi", "person", "Narendra Modi"),
    ("jerome_powell", "person", "Jerome Powell"),
    ("elon_musk", "person", "Elon Musk"),
]

# Company nodes mapping to tickers
COMPANY_NODES = [
    ("RELIANCE.NS", "company", "Reliance Industries"),
    ("TCS.NS", "company", "Tata Consultancy Services"),
    ("INFY.NS", "company", "Infosys"),
    ("HDFCBANK.NS", "company", "HDFC Bank"),
    ("ICICIBANK.NS", "company", "ICICI Bank"),
    ("HINDUNILVR.NS", "company", "Hindustan Unilever"),
    ("SBIN.NS", "company", "State Bank of India"),
    ("BHARTIARTL.NS", "company", "Bharti Airtel"),
    ("ITC.NS", "company", "ITC Limited"),
    ("KOTAKBANK.NS", "company", "Kotak Mahindra Bank"),
    ("LT.NS", "company", "Larsen & Toubro"),
    ("BAJFINANCE.NS", "company", "Bajaj Finance"),
    ("AXISBANK.NS", "company", "Axis Bank"),
    ("ASIANPAINT.NS", "company", "Asian Paints"),
    ("MARUTI.NS", "company", "Maruti Suzuki"),
    ("TITAN.NS", "company", "Titan Company"),
    ("SUNPHARMA.NS", "company", "Sun Pharmaceutical"),
    ("ULTRACEMCO.NS", "company", "UltraTech Cement"),
    ("WIPRO.NS", "company", "Wipro"),
    ("ONGC.NS", "company", "ONGC"),
    ("NTPC.NS", "company", "NTPC Limited"),
    ("POWERGRID.NS", "company", "Power Grid Corporation"),
    ("TECHM.NS", "company", "Tech Mahindra"),
    ("HCLTECH.NS", "company", "HCL Technologies"),
    ("NESTLEIND.NS", "company", "Nestle India"),
    ("HAL.NS", "company", "Hindustan Aeronautics"),
    ("BEL.NS", "company", "Bharat Electronics"),
    ("INDIGO.NS", "company", "InterGlobe Aviation"),
    ("COALINDIA.NS", "company", "Coal India"),
    ("TATASTEEL.NS", "company", "Tata Steel"),
]

# Macro relationships: source -> target, relationship type, weight
MACRO_EDGES = [
    # Countries -> Commodities
    ("middle_east", "crude_oil", "supplies", 0.9),
    ("russia", "crude_oil", "supplies", 0.7),
    ("russia", "natural_gas", "supplies", 0.8),
    ("australia", "steel", "supplies", 0.6),  # supplies iron ore for steel
    ("china", "copper", "supplies", 0.7),
    ("china", "semiconductors", "supplies", 0.6),
    ("china", "api_ingredients", "supplies", 0.8),

    # Commodities -> Sectors
    ("crude_oil", "energy_utilities", "benefits", 0.6),
    ("crude_oil", "aviation", "increases_cost_of", -0.8),
    ("crude_oil", "paints", "increases_cost_of", -0.7),
    ("crude_oil", "automobiles", "increases_cost_of", -0.3),
    ("natural_gas", "energy_utilities", "benefits", 0.5),
    ("coal", "energy_utilities", "benefits", 0.7),
    ("steel", "infrastructure", "increases_cost_of", -0.5),
    ("steel", "automobiles", "increases_cost_of", -0.4),
    ("copper", "technology", "increases_cost_of", -0.2),
    ("semiconductors", "technology", "supplies", 0.8),
    ("semiconductors", "automobiles", "supplies", 0.7),
    ("api_ingredients", "pharmaceuticals", "supplies", 0.9),
    ("gold", "jewellery", "increases_cost_of", -0.4),

    # Macro/Geopolitical US -> Tech (Indian IT exports to US)
    ("usa", "technology", "depends_on", 0.8),
    ("usa", "banking_finance", "influences", 0.6),

    # Influential Leaders -> Countries/Sectors/Commodities
    ("donald_trump", "usa", "influences", 0.9),
    ("donald_trump", "technology", "affects", -0.4),  # Tariffs disrupt global tech supply chains
    ("donald_trump", "crude_oil", "affects", 0.6),     # Domestic energy production increase
    ("narendra_modi", "india", "influences", 0.9),
    ("narendra_modi", "infrastructure", "benefits", 0.8), # Infrastructure expansion focus
    ("narendra_modi", "energy_utilities", "benefits", 0.7), # Green energy push
    ("jerome_powell", "banking_finance", "influences", 0.9), # FED rate hikes/cuts
    ("jerome_powell", "usa", "influences", 0.7),
    ("elon_musk", "automobiles", "benefits", 0.7),     # Tesla / EV market expansion
    ("elon_musk", "technology", "influences", 0.8),

    # Sectors -> Companies
    ("technology", "TCS.NS", "contains", 1.0),
    ("technology", "INFY.NS", "contains", 1.0),
    ("technology", "WIPRO.NS", "contains", 1.0),
    ("technology", "TECHM.NS", "contains", 1.0),
    ("technology", "HCLTECH.NS", "contains", 1.0),

    ("banking_finance", "HDFCBANK.NS", "contains", 1.0),
    ("banking_finance", "ICICIBANK.NS", "contains", 1.0),
    ("banking_finance", "SBIN.NS", "contains", 1.0),
    ("banking_finance", "KOTAKBANK.NS", "contains", 1.0),
    ("banking_finance", "AXISBANK.NS", "contains", 1.0),
    ("banking_finance", "BAJFINANCE.NS", "contains", 1.0),

    ("energy_utilities", "RELIANCE.NS", "contains", 0.5),  # Reliance is oil-to-chemicals
    ("energy_utilities", "ONGC.NS", "contains", 1.0),
    ("energy_utilities", "NTPC.NS", "contains", 1.0),
    ("energy_utilities", "POWERGRID.NS", "contains", 1.0),
    ("energy_utilities", "COALINDIA.NS", "contains", 1.0),

    ("consumer_fmcg", "HINDUNILVR.NS", "contains", 1.0),
    ("consumer_fmcg", "ITC.NS", "contains", 1.0),
    ("consumer_fmcg", "NESTLEIND.NS", "contains", 1.0),

    ("automobiles", "MARUTI.NS", "contains", 1.0),

    ("metals_mining", "TATASTEEL.NS", "contains", 1.0),

    ("defense_aerospace", "HAL.NS", "contains", 1.0),
    ("defense_aerospace", "BEL.NS", "contains", 1.0),

    ("aviation", "INDIGO.NS", "contains", 1.0),

    ("pharmaceuticals", "SUNPHARMA.NS", "contains", 1.0),

    ("infrastructure", "LT.NS", "contains", 1.0),

    ("paints", "ASIANPAINT.NS", "contains", 1.0),

    ("cement", "ULTRACEMCO.NS", "contains", 1.0),

    ("jewellery", "TITAN.NS", "contains", 1.0),

    # Indirect/Direct Commodity to Company Links
    ("crude_oil", "ONGC.NS", "benefits", 0.8),
    ("crude_oil", "RELIANCE.NS", "benefits", 0.4),  # Refiners benefit slightly from refining margins
    ("coal", "COALINDIA.NS", "benefits", 0.9),
    ("steel", "TATASTEEL.NS", "benefits", 0.8),
    ("gold", "TITAN.NS", "affects", -0.3),  # High gold prices depress retail volumes
]


def seed_knowledge_graph(graph: IKnowledgeGraph) -> None:
    """Populate the economic graph with nodes and connections."""
    for nid, ntype, label in MACRO_NODES:
        graph.add_node(GraphNode(node_id=nid, node_type=ntype, label=label))

    for nid, ntype, label in COMPANY_NODES:
        graph.add_node(
            GraphNode(
                node_id=nid,
                node_type=ntype,
                label=label,
                metadata={"exchange": "NSE", "country": "India"},
            )
        )

    for src, tgt, rel, weight in MACRO_EDGES:
        graph.add_edge(GraphEdge(source_id=src, target_id=tgt, relationship=rel, weight=weight))
