"""
Crop Agronomic Knowledge Tool
Read-only database of crop physiological ranges, nutritional deficiencies, leaf symptom diagnostics,
crop suitability matrices, soil chemistry interpretations, and agronomic best practices.
"""
from typing import Dict, Any, List, Optional
from ai_agronomist.tools.base import BaseTool

# Curated scientific agronomic thresholds for major crops
CROP_THRESHOLDS = {
    "wheat": {
        "crop_name": "Wheat (गेहूं)",
        "scientific_name": "Triticum aestivum",
        "season": "Rabi (Winter)",
        "optimal_ph_range": (6.0, 7.5),
        "soil_moisture_min_pct": 40.0,
        "soil_moisture_opt_pct": 55.0,
        "soil_moisture_max_pct": 70.0,
        "soil_temp_opt_c": (15.0, 25.0),
        "ec_tolerance_ds_m": 3.0,
        "soil_type_preference": "Well-drained fertile loam or clay loam",
        "npk_requirement_ratio": "120:60:40 (N:P2O5:K2O kg/ha)",
        "critical_growth_stages": [
            "CRI (Crown Root Initiation at 21 days)",
            "Tillering (40-45 days)",
            "Jointing",
            "Flowering / Heading",
            "Milking / Grain Filling",
            "Dough stage",
        ],
        "irrigation_guideline": "5 to 6 irrigations; CRI stage is the most critical where moisture stress causes severe yield loss.",
    },
    "cotton": {
        "crop_name": "Cotton (कपास)",
        "scientific_name": "Gossypium hirsutum",
        "season": "Kharif (Monsoon / Summer)",
        "optimal_ph_range": (5.8, 8.0),
        "soil_moisture_min_pct": 35.0,
        "soil_moisture_opt_pct": 50.0,
        "soil_moisture_max_pct": 65.0,
        "soil_temp_opt_c": (20.0, 32.0),
        "ec_tolerance_ds_m": 4.0,
        "soil_type_preference": "Deep black cotton soil (Vertisols) or fertile sandy loam with good drainage",
        "npk_requirement_ratio": "120:60:60 (N:P2O5:K2O kg/ha)",
        "critical_growth_stages": [
            "Square formation (squaring)",
            "Peak flowering",
            "Boll development & elongation",
            "Boll bursting",
        ],
        "irrigation_guideline": "Avoid moisture stress during flowering and boll formation; sensitive to waterlogging.",
    },
    "tomato": {
        "crop_name": "Tomato (टमाटर)",
        "scientific_name": "Solanum lycopersicum",
        "season": "Rabi / Kharif / Polyhouse Year-round",
        "optimal_ph_range": (6.0, 7.0),
        "soil_moisture_min_pct": 50.0,
        "soil_moisture_opt_pct": 65.0,
        "soil_moisture_max_pct": 75.0,
        "soil_temp_opt_c": (18.0, 27.0),
        "ec_tolerance_ds_m": 2.5,
        "soil_type_preference": "Rich, well-drained sandy loam or silt loam rich in organic matter",
        "npk_requirement_ratio": "150:100:100 (N:P2O5:K2O kg/ha)",
        "critical_growth_stages": [
            "Transplanting recovery",
            "Vegetative branching",
            "Flowering",
            "Fruit setting",
            "Fruit ripening",
        ],
        "irrigation_guideline": "Consistent moisture needed; moisture fluctuation causes blossom end rot and fruit cracking.",
    },
    "mustard": {
        "crop_name": "Mustard / Sarson (सरसों)",
        "scientific_name": "Brassica juncea",
        "season": "Rabi (Winter)",
        "optimal_ph_range": (6.0, 7.5),
        "soil_moisture_min_pct": 35.0,
        "soil_moisture_opt_pct": 48.0,
        "soil_moisture_max_pct": 65.0,
        "soil_temp_opt_c": (15.0, 25.0),
        "ec_tolerance_ds_m": 3.0,
        "soil_type_preference": "Light to heavy loam, drought hardy, good drainage",
        "npk_requirement_ratio": "80:40:40 (N:P2O5:K2O kg/ha) + 20-40 kg Sulphur",
        "critical_growth_stages": ["Flowering", "Siliqua / Pod development"],
        "irrigation_guideline": "2 to 3 light irrigations; highly susceptible to waterlogging.",
    },
    "chickpea": {
        "crop_name": "Chickpea / Gram (चना)",
        "scientific_name": "Cicer arietinum",
        "season": "Rabi (Winter)",
        "optimal_ph_range": (6.0, 7.5),
        "soil_moisture_min_pct": 30.0,
        "soil_moisture_opt_pct": 45.0,
        "soil_moisture_max_pct": 60.0,
        "soil_temp_opt_c": (15.0, 25.0),
        "ec_tolerance_ds_m": 1.5,  # Sensitive to salinity
        "soil_type_preference": "Well-aerated sandy loam to clay loam; intolerant of water stagnation",
        "npk_requirement_ratio": "20:40:20 (N:P2O5:K2O kg/ha) - Legume, fixes atmospheric nitrogen",
        "critical_growth_stages": ["Branching", "Pre-flowering", "Pod filling"],
        "irrigation_guideline": "1 to 2 light irrigations; excess moisture causes vegetative runaway and wilt.",
    },
    "maize": {
        "crop_name": "Maize / Corn (मक्का)",
        "scientific_name": "Zea mays",
        "season": "Kharif / Spring / Rabi",
        "optimal_ph_range": (5.8, 7.5),
        "soil_moisture_min_pct": 45.0,
        "soil_moisture_opt_pct": 60.0,
        "soil_moisture_max_pct": 75.0,
        "soil_temp_opt_c": (18.0, 30.0),
        "ec_tolerance_ds_m": 2.5,
        "soil_type_preference": "Deep, well-drained fertile loam rich in organic matter",
        "npk_requirement_ratio": "120:60:40 (N:P2O5:K2O kg/ha)",
        "critical_growth_stages": ["Taselling", "Silking", "Grain filling"],
        "irrigation_guideline": "Critical at silking and grain filling; cannot tolerate standing water.",
    },
    "rice": {
        "crop_name": "Rice / Paddy (धान)",
        "scientific_name": "Oryza sativa",
        "season": "Kharif (Monsoon)",
        "optimal_ph_range": (5.0, 6.8),
        "soil_moisture_min_pct": 65.0,
        "soil_moisture_opt_pct": 80.0,
        "soil_moisture_max_pct": 95.0,
        "soil_temp_opt_c": (22.0, 32.0),
        "ec_tolerance_ds_m": 3.0,
        "soil_type_preference": "Heavy clayey or silty soils with low percolation",
        "npk_requirement_ratio": "100:50:50 (N:P2O5:K2O kg/ha) + Zinc",
        "critical_growth_stages": ["Tillering", "Panicle Initiation", "Flowering"],
        "irrigation_guideline": "Continuous shallow water layer during tillering and panicle development.",
    },
    "sugarcane": {
        "crop_name": "Sugarcane (गन्ना)",
        "scientific_name": "Saccharum officinarum",
        "season": "Perennial / Annual (Spring / Autumn planting)",
        "optimal_ph_range": (6.0, 7.5),
        "soil_moisture_min_pct": 50.0,
        "soil_moisture_opt_pct": 65.0,
        "soil_moisture_max_pct": 80.0,
        "soil_temp_opt_c": (20.0, 32.0),
        "ec_tolerance_ds_m": 2.0,
        "soil_type_preference": "Deep, well-drained fertile loam or clay loam with neutral pH",
        "npk_requirement_ratio": "250:100:120 (N:P2O5:K2O kg/ha)",
        "critical_growth_stages": [
            "Germination / Formative stage",
            "Grand growth (Tillering & Stalk elongation)",
            "Maturity & Ripening",
        ],
        "irrigation_guideline": "High water requirement; regular irrigation required during formative and grand growth stages.",
    },
    "general": {
        "crop_name": "General Field Crop",
        "optimal_ph_range": (6.0, 7.5),
        "soil_moisture_min_pct": 40.0,
        "soil_moisture_opt_pct": 50.0,
        "soil_moisture_max_pct": 70.0,
        "soil_temp_opt_c": (18.0, 28.0),
        "ec_tolerance_ds_m": 2.0,
        "soil_type_preference": "Well-drained loam",
        "critical_growth_stages": ["Vegetative", "Reproductive", "Maturation"],
        "irrigation_guideline": "Maintain optimal root zone moisture avoiding drought and waterlogging.",
    },
}

# Soil chemistry reference data
SOIL_CHEMISTRY_KNOWLEDGE = {
    "ph_scale": {
        "ideal_range": (6.5, 7.5),
        "interpretation": {
            "strongly_acidic": {"range": (0.0, 5.5), "status": "Strongly Acidic", "implications": "Al/Mn toxicity, P fixation, Ca/Mg deficiency; requires agricultural lime (calcium carbonate)."},
            "moderately_acidic": {"range": (5.5, 6.5), "status": "Moderately Acidic", "implications": "Acceptable for potatoes and tea; phosphorus availability reduced; gypsum or lime may help."},
            "neutral_ideal": {"range": (6.5, 7.5), "status": "Neutral / Optimal", "implications": "Ideal for almost all agricultural crops (Wheat, Cotton, Mustard, Vegetables); maximum nutrient bioavailability for N, P, K, S, Ca, Mg."},
            "moderately_alkaline": {"range": (7.5, 8.5), "status": "Moderately Alkaline", "implications": "Common in arid/semi-arid regions; micronutrient availability (Fe, Zn, Mn) restricted; apply gypsum and organic compost."},
            "strongly_alkaline": {"range": (8.5, 14.0), "status": "Strongly Alkaline / Sodic", "implications": "High exchangeable sodium percentage; poor physical soil structure, water infiltration severely hindered; requires agricultural gypsum (calcium sulfate) and heavy organic matter."},
        },
    },
    "electrical_conductivity": {
        "unit": "dS/m (deciSiemens per metre) at 25°C",
        "interpretation": {
            "non_saline": {"range": (0.0, 1.2), "status": "Non-saline / Optimal", "implications": "No restriction for any crop growth; normal water and nutrient uptake by roots."},
            "slightly_saline": {"range": (1.2, 2.5), "status": "Slightly Saline", "implications": "Yield of very sensitive crops (pulses, beans, strawberry) may be slightly reduced; tolerant crops unaffected."},
            "moderately_saline": {"range": (2.5, 4.0), "status": "Moderately Saline", "implications": "Yield of many crops restricted; causes osmotic pressure hindering root water absorption (physiological drought)."},
            "highly_saline": {"range": (4.0, 100.0), "status": "Highly Saline", "implications": "Severe osmotic stress; only salt-tolerant crops (barley, cotton, sugarbeet) can survive; leaching with good quality water required."},
        },
    },
    "npk_nutrients": {
        "nitrogen": {
            "symbol": "N",
            "primary_function": "Drives rapid vegetative growth, leaf and stem expansion, and chlorophyll synthesis for green color and photosynthesis.",
            "deficiency_symptoms": "Uniform yellowing (chlorosis) starting on older lower leaves; stunted spindly growth.",
            "excess_symptoms": "Overly dark green leaves, excessive vegetative foliage, delayed flowering/maturity, weak lodging stems, increased susceptibility to insect pests.",
        },
        "phosphorus": {
            "symbol": "P",
            "primary_function": "Promotes deep root development, energy transfer (ATP synthesis), early plant vigor, flowering, pollination, and seed formation.",
            "deficiency_symptoms": "Purplish or reddish-bronze discoloration along margins of older leaves; stunted root systems; delayed crop maturity.",
            "excess_symptoms": "Interferes with the uptake of micronutrients, particularly Zinc (Zn) and Iron (Fe).",
        },
        "potassium": {
            "symbol": "K",
            "primary_function": "Regulates stomatal opening and closing (water retention), enzyme activation, carbohydrate translocation, lodging resistance, and disease/drought stress tolerance.",
            "deficiency_symptoms": "Marginal leaf scorch, yellowing and browning (firing) starting along leaf edges of older leaves; weak stems susceptible to lodging.",
            "excess_symptoms": "Can antagonize and reduce plant uptake of Magnesium (Mg) and Calcium (Ca).",
        },
        "npk_difference_summary": "Nitrogen (N) builds leaf area, green color, and plant proteins; Phosphorus (P) builds root depth, energy storage (ATP), and seeds; Potassium (K) regulates water transpiration, disease defense, and stem strength.",
    },
}

# Agronomic best practices reference
AGRONOMIC_PRACTICES = {
    "crop_rotation": {
        "definition": "The agronomic practice of growing a planned series of different crops in succession on the same parcel of land across cropping seasons.",
        "key_benefits": [
            "Breaks insect pest, nematode, and soil-borne fungal disease lifecycles that host on a specific plant family.",
            "Nutrient replenishment: Legumes (chickpea, mung bean, cowpea) fix atmospheric nitrogen into the soil, reducing synthetic urea requirements for succeeding cereal crops.",
            "Different rooting depths: Alternating tap-rooted crops (cotton, pigeon pea) with fibrous-rooted crops (wheat, maize) improves soil aeration and draws nutrients from varied depths.",
            "Weed suppression: Changing crop canopies and sowing dates suppresses problematic weed species.",
        ],
        "example_rotations": [
            "Paddy (Kharif) -> Wheat (Rabi) -> Green gram / Moong (Summer/Zaid)",
            "Cotton (Kharif) -> Wheat / Mustard (Rabi)",
            "Maize (Kharif) -> Chickpea / Mustard (Rabi)",
            "Soybean (Kharif) -> Wheat (Rabi)",
        ],
    },
    "soil_fertility_improvement": {
        "principles": [
            "Organic matter addition: Incorporate 10-15 tonnes/ha of well-decomposed Farm Yard Manure (FYM) or 5 tonnes/ha vermicompost before land preparation.",
            "Green manuring: Sow Sesbania (Dhaincha) or Sunn hemp (Crotalaria juncea) during pre-monsoon and incorporate into soil at 45 days (flowering stage) to add 60-80 kg N/ha.",
            "Bio-fertilizers: Seed inoculation or soil application of Azotobacter/Azospirillum (nitrogen fixers) and PSB (Phosphate Solubilizing Bacteria).",
            "Crop residue retention: Mulch and incorporate crop stubble rather than burning, enhancing microbial biomass and soil carbon.",
            "Balanced fertilization: Base nutrient application on official Soil Health Card lab recommendations using 4R principles (Right source, Right rate, Right time, Right place).",
        ],
    },
    "organic_farming": {
        "definition": "A holistic agricultural production management system that promotes and enhances agro-ecosystem health, biodiversity, biological cycles, and soil biological activity without synthetic chemicals.",
        "core_principles": [
            "Health: Sustaining and enhancing the health of soil, plants, animals, humans, and the planet as one and indivisible.",
            "Ecology: Basing farming systems on living ecological systems and cycles, working with them and helping sustain them.",
            "Fairness: Building relationships that ensure fairness regarding the common environment and life opportunities.",
            "Care: Managing agriculture in a precautionary and responsible manner to protect the health and well-being of current and future generations.",
        ],
        "key_practices": [
            "Zero synthetic chemical fertilizers and pesticides; reliance on compost, Panchagavya, Jeevamrit, and vermicompost.",
            "Biological pest control: Trichoderma, Pseudomonas fluorescens, Neem seed kernel extract (NSKE 5%), pheromone traps, and light traps.",
            "Companion planting, intercropping, and crop rotations to encourage natural predators and beneficial pollinators.",
        ],
    },
    "over_irrigation": {
        "disadvantages": [
            "Root Hypoxia & Asphyxiation: Soil pores fill with water, displacing soil oxygen; roots suffocate, halting cellular respiration and nutrient uptake.",
            "Root Rot & Fungal Pathogens: Saturated soil creates prime conditions for Pythium, Phytophthora, Fusarium, and Rhizoctonia damping-off and vascular wilt.",
            "Nutrient Leaching: Soluble nitrogen (nitrates) and potassium leach down past the active root zone into groundwater, wasting fertilizer and contaminating aquifers.",
            "Denitrification: Anaerobic microbes convert soil nitrate into nitrous oxide and nitrogen gas, causing rapid nitrogen loss.",
            "Salinization: In arid regions, waterlogging brings deep dissolved salts to the surface through capillary rise, leaving a white salt crust when water evaporates.",
        ],
    },
    "monsoon_precautions": {
        "precautions": [
            "Drainage Infrastructure: Clean and deepen field perimeter trenches and drainage furrows to allow surplus runoff to escape rapidly within 12-24 hours.",
            "Raised Bed / Broad Bed Furrow (BBF) Planting: For crops sensitive to waterlogging (maize, cotton, soybean, vegetables), plant on raised ridges or beds so roots stay above saturated furrows.",
            "Avoid Fertilizer Application Before Downpours: Do not broadcast urea or soluble fertilizers immediately prior to heavy rains to prevent runoff wash-off and leaching.",
            "Preventive Bio-Fungicide Protection: High humidity invites foliar blight and damping-off; spray protective biocides like Trichoderma viride or Pseudomonas fluorescens or copper oxychloride as weather permits.",
            "Field Bund Strengthening: Repair and reinforce farm bunds to control water entry and prevent gully soil erosion.",
        ],
    },
    "soil_testing": {
        "importance": "Laboratory soil testing is the scientific baseline of precision agriculture. It provides exact quantitative values for available macro-nutrients (N, P, K), secondary nutrients (S, Ca, Mg), micronutrients (Zn, Fe, Cu, Mn, B), soil organic carbon, and electrical conductivity.",
        "recommended_frequency": "Every 2 to 3 years, or immediately before initiating a high-value commercial crop cycle.",
        "complementary_role": "FertoBot in-situ IoT probes measure real-time dynamic physical parameters (moisture, temperature, volumetric bulk EC, and continuous trend indicators) 24/7, while accredited laboratory wet-chemistry tests provide certified chemical calibration for total soil nutrient reserves.",
    },
}

SYMPTOM_DIAGNOSTICS = {
    "yellow_leaves": {
        "primary_hypotheses": [
            {
                "condition": "Nitrogen (N) Deficiency",
                "pattern": "Uniform yellowing (chlorosis) beginning on older/lower leaves while upper leaves remain pale green. Plant is stunted with thin stems.",
                "remedy": "Foliar application of 1-2% urea spray or top-dressing nitrogen based on soil test.",
            },
            {
                "condition": "Waterlogging / Overwatering (Root Hypoxia)",
                "pattern": "Lower leaves turn pale yellow; root hypoxia prevents nutrient uptake; soil feels saturated or muddy (>65% moisture).",
                "remedy": "Cease irrigation, improve trench drainage, aerate soil, apply foliar nutrients once drained.",
            },
            {
                "condition": "Iron (Fe) or Zinc (Zn) Micronutrient Deficiency",
                "pattern": "Interveinal chlorosis appearing first on younger/top leaves; leaf veins stay dark green while tissue between veins turns yellow/white.",
                "remedy": "Foliar spray of chelated iron (Fe-EDTA 0.1%) or Zinc Sulfate (0.5%) with 0.25% lime.",
            },
            {
                "condition": "Viral Infection (e.g. Tomato Yellow Leaf Curl / Mosaic)",
                "pattern": "Mottling, mosaic pattern, leaf curling upwards, stunted bushy plant; spread by whiteflies or aphids.",
                "remedy": "Rogue out and destroy infected plants; install yellow sticky traps; spray neem oil or systemic insecticide for vectors.",
            },
        ],
        "required_clarifications": [
            "Which crop species is planted?",
            "Are the yellow leaves at the bottom (older) or top (newer) of the plant?",
            "When was the plot last irrigated?",
            "Is there any leaf curling or vein distortion?",
        ],
    },
    "wilting": {
        "primary_hypotheses": [
            {
                "condition": "Soil Moisture Deficit / Drought Stress",
                "pattern": "Leaves roll inward and droop during midday heat; recovers slightly at dawn; soil is dry below 35% moisture.",
                "remedy": "Apply measured irrigation targeting root zone depth immediately.",
            },
            {
                "condition": "Root Rot / Fungal Vascular Wilt (Fusarium/Rhizoctonia/Pythium)",
                "pattern": "Leaves wilt despite moist or saturated soil; vascular browning visible inside stem cut; roots are brown/mushy.",
                "remedy": "Trichoderma bio-fungicide drench; avoid standing water; improve soil drainage.",
            },
        ],
        "required_clarifications": [
            "Is the soil dry or wet around the root zone?",
            "Do plants recover during cooler night/morning hours?",
        ],
    },
}


class CropKnowledgeTool(BaseTool):
    """
    Read-only agronomic knowledge tool for looking up crop thresholds, soil chemistry,
    differential diagnostics, suitability, and agronomic best practices.
    """

    @property
    def name(self) -> str:
        return "crop_knowledge"

    @property
    def description(self) -> str:
        return (
            "Retrieves agronomic thresholds (soil moisture, temperature, pH, EC), differential "
            "diagnostic trees for symptoms, soil chemistry guidelines (pH, EC, NPK differences), "
            "crop suitability evaluation matrices, and sustainable agronomic practices."
        )

    async def execute(
        self,
        crop: Optional[str] = None,
        symptom: Optional[str] = None,
        topic: Optional[str] = None,
        telemetry_readings: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        crop_clean = (crop or "general").strip().lower()
        thresholds = CROP_THRESHOLDS.get(crop_clean, CROP_THRESHOLDS.get("general"))

        # Symptom diagnostics lookup
        diagnostic_data = None
        if symptom:
            s_clean = symptom.strip().lower()
            if any(w in s_clean for w in ["yellow", "chloros", "पीली", "पीला"]):
                diagnostic_data = SYMPTOM_DIAGNOSTICS["yellow_leaves"]
            elif any(w in s_clean for w in ["wilt", "dry", "मुरझा", "सूख"]):
                diagnostic_data = SYMPTOM_DIAGNOSTICS["wilting"]

        # Topic lookup
        topic_data = None
        if topic:
            t_clean = topic.strip().lower()
            if "ph" in t_clean:
                topic_data = SOIL_CHEMISTRY_KNOWLEDGE["ph_scale"]
            elif "ec" in t_clean or "conduct" in t_clean or "salin" in t_clean:
                topic_data = SOIL_CHEMISTRY_KNOWLEDGE["electrical_conductivity"]
            elif "npk" in t_clean or "nitrogen" in t_clean or "phosphorus" in t_clean:
                topic_data = SOIL_CHEMISTRY_KNOWLEDGE["npk_nutrients"]
            elif "rotation" in t_clean:
                topic_data = AGRONOMIC_PRACTICES["crop_rotation"]
            elif "fertility" in t_clean or "improve" in t_clean:
                topic_data = AGRONOMIC_PRACTICES["soil_fertility_improvement"]
            elif "organic" in t_clean:
                topic_data = AGRONOMIC_PRACTICES["organic_farming"]
            elif "over_irrigation" in t_clean or "disadvantage" in t_clean:
                topic_data = AGRONOMIC_PRACTICES["over_irrigation"]
            elif "monsoon" in t_clean or "rain" in t_clean:
                topic_data = AGRONOMIC_PRACTICES["monsoon_precautions"]
            elif "testing" in t_clean or "test" in t_clean:
                topic_data = AGRONOMIC_PRACTICES["soil_testing"]

        # Crop suitability matching based on provided telemetry readings
        suitability_matches = []
        if telemetry_readings:
            ph = telemetry_readings.get("ph")
            ec = telemetry_readings.get("electrical_conductivity_ds_m")
            moisture = telemetry_readings.get("soil_moisture_pct")
            temp = telemetry_readings.get("soil_temperature_c")

            for c_id, c_data in CROP_THRESHOLDS.items():
                if c_id == "general":
                    continue
                ph_range = c_data.get("optimal_ph_range", (6.0, 7.5))
                ec_limit = c_data.get("ec_tolerance_ds_m", 3.0)

                ph_ok = ph is None or (ph_range[0] - 0.3 <= ph <= ph_range[1] + 0.3)
                ec_ok = ec is None or (ec <= ec_limit)

                score = 0
                reasons = []
                if ph_ok:
                    score += 50
                    reasons.append(f"pH {ph} is within optimal range ({ph_range[0]}-{ph_range[1]})")
                else:
                    reasons.append(f"pH {ph} outside optimal range ({ph_range[0]}-{ph_range[1]})")

                if ec_ok:
                    score += 50
                    reasons.append(f"EC {ec} dS/m within tolerance (max {ec_limit} dS/m)")
                else:
                    reasons.append(f"EC {ec} dS/m exceeds tolerance ({ec_limit} dS/m)")

                suitability_matches.append({
                    "crop_id": c_id,
                    "crop_name": c_data.get("crop_name"),
                    "season": c_data.get("season"),
                    "suitability_score": score,
                    "is_suitable": score >= 80,
                    "reasons": reasons,
                    "soil_type_preference": c_data.get("soil_type_preference"),
                })

            # Sort by suitability score descending
            suitability_matches.sort(key=lambda x: x["suitability_score"], reverse=True)

        return {
            "source": "Agronomic Diagnostic Knowledgebase v3.0 (Read-Only)",
            "crop": crop_clean,
            "thresholds": thresholds,
            "diagnostic_data": diagnostic_data,
            "topic_data": topic_data,
            "suitability_matches": suitability_matches if suitability_matches else None,
            "has_specific_crop_match": crop_clean in CROP_THRESHOLDS,
            "all_supported_crops": [c["crop_name"] for c in CROP_THRESHOLDS.values() if "crop_name" in c],
        }
