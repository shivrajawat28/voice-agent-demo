"""
Crop Symptom & Agronomic Specialist Agent
Analyzes visual and physiological crop symptoms, soil nutrient balance, crop suitability,
and sustainable soil management grounded in simulated soil NPK, pH, and EC telemetry.
Illustrative sensor values are never claimed as lab-confirmed nutrient deficiencies.
"""
import re
from typing import List, Dict, Any, Optional
from ai_agronomist.agents.base import BaseAgent, AgentContext
from ai_agronomist.models.conversation import AgentResult
from ai_agronomist.tools.base import BaseTool


class CropSymptomAgent(BaseAgent):
    @property
    def agent_id(self) -> str:
        return "crop_symptom"

    @property
    def name(self) -> str:
        return "Crop Symptom & Agronomy Specialist"

    @property
    def description(self) -> str:
        return (
            "Diagnoses physiological crop symptoms (chlorosis, leaf spots, wilting), evaluates crop "
            "suitability and rotation, interprets soil chemistry (pH, EC, NPK functions), and provides "
            "agronomic recommendations grounded in simulated soil telemetry."
        )

    @property
    def permitted_tools(self) -> List[str]:
        return ["crop_knowledge", "farm_telemetry", "latest_telemetry"]

    async def execute(
        self,
        context: AgentContext,
        tools: Dict[str, BaseTool],
    ) -> AgentResult:
        query_lower = context.query.lower()
        is_hindi = context.language.lower().startswith("hi") or bool(
            re.search(r"[\u0900-\u097F]", context.query)
        )
        zone_id = getattr(context, "zone_id", None) or "DEMO-ZONE-001"

        # 1. Retrieve telemetry for target zone
        tel_tool = tools.get("latest_telemetry") or tools.get("farm_telemetry")
        tel_data: Dict[str, Any] = {}
        if tel_tool:
            tel_data = await tel_tool.execute(zone_id=zone_id)

        crop_from_tel = tel_data.get("crop")
        variety_from_tel = tel_data.get("variety")
        stage_from_tel = tel_data.get("growth_stage")

        n_val = tel_data.get("nitrogen_mg_kg")
        p_val = tel_data.get("phosphorus_mg_kg")
        k_val = tel_data.get("potassium_mg_kg")
        ph_val = tel_data.get("ph")
        ec_val = tel_data.get("electrical_conductivity_ds_m")
        moisture_val = tel_data.get("soil_moisture_pct")
        temp_val = tel_data.get("soil_temperature_c")

        # 2. Detect crop mentioned explicitly in query or use zone crop
        detected_crop = None
        for crop_name in ["wheat", "cotton", "rice", "tomato", "potato", "mustard", "chickpea", "gram", "maize", "गेहूं", "कपास", "धान", "टमाटर", "सरसों", "चना", "मक्का"]:
            if crop_name in query_lower:
                if any(w in crop_name for w in ["गेहूं", "wheat"]):
                    detected_crop = "wheat"
                elif any(w in crop_name for w in ["कपास", "cotton"]):
                    detected_crop = "cotton"
                elif any(w in crop_name for w in ["धान", "rice"]):
                    detected_crop = "rice"
                elif any(w in crop_name for w in ["टमाटर", "tomato"]):
                    detected_crop = "tomato"
                elif any(w in crop_name for w in ["सरसों", "mustard"]):
                    detected_crop = "mustard"
                elif any(w in crop_name for w in ["चना", "chickpea", "gram"]):
                    detected_crop = "chickpea"
                elif any(w in crop_name for w in ["मक्का", "maize"]):
                    detected_crop = "maize"
                else:
                    detected_crop = crop_name
                break

        query_crop_detected = detected_crop is not None
        if not detected_crop and crop_from_tel:
            detected_crop = crop_from_tel

        # 3. Detect inquiry topic / intent
        detected_topic = None
        detected_symptom = None

        if any(w in query_lower for w in ["aur kya uga", "kya uga sakte", "suitab", "best crop", "kaunsi crop", "kaunsi fasal", "what to grow"]):
            detected_topic = "crop_suitability"
        elif any(w in query_lower for w in ["ph 6.8", "soil ph", "ph ka kya matlab", "ph scale", "पीएच"]):
            detected_topic = "ph"
        elif any(w in query_lower for w in ["difference", "diff", "kya antar", "kya difference", "nitrogen aur phosphorus"]):
            detected_topic = "npk"
        elif any(w in query_lower for w in ["electrical conductivity", "ec ka", "salinity", "चालकता"]):
            detected_topic = "ec"
        elif any(w in query_lower for w in ["crop rotation", "rotation kya", "फसल चक्र"]):
            detected_topic = "rotation"
        elif any(w in query_lower for w in ["fertility", "fertility improve", "उर्वरता", "उपजाऊ"]):
            detected_topic = "fertility"
        elif any(w in query_lower for w in ["organic", "जैविक खेती", "organic farming"]):
            detected_topic = "organic"
        elif any(w in query_lower for w in ["soil testing", "soil test", "मिट्टी परीक्षण", "लैब टेस्ट"]):
            detected_topic = "testing"
        elif any(w in query_lower for w in ["yellow", "peeli", "पीली", "chloros"]):
            detected_symptom = "yellow_leaves"
        elif any(w in query_lower for w in ["wilt", "dry", "मुरझा", "सूख"]):
            detected_symptom = "wilting"
        elif any(w in query_lower for w in ["npk", "नाइट्रोजन", "फॉस्फोरस", "पोटाश", "पोषक"]):
            detected_symptom = "nutrient_inquiry"

        # 4. Execute knowledge tool
        crop_tool = tools.get("crop_knowledge")
        knowledge_output = {}
        if crop_tool:
            knowledge_output = await crop_tool.execute(
                crop=detected_crop,
                symptom=detected_symptom,
                topic=detected_topic,
                telemetry_readings=tel_data,
            )

        evidence: List[str] = [
            f"Zone: {tel_data.get('zone_name', zone_id)}",
            f"Cultivated Crop: {detected_crop or 'Unspecified'} ({variety_from_tel or 'standard'}, stage: {stage_from_tel or 'vegetative'})",
            f"Simulated Soil Moisture: {moisture_val}%" if moisture_val is not None else "Soil Moisture: Missing",
            f"Simulated Soil Temperature: {temp_val}°C" if temp_val is not None else "Soil Temperature: Missing",
            f"Simulated Nitrogen (N): {f'{n_val} mg/kg' if n_val is not None else 'MISSING / UNCALIBRATED'}",
            f"Simulated Phosphorus (P): {p_val} mg/kg" if p_val is not None else "Phosphorus: Missing",
            f"Simulated Potassium (K): {k_val} mg/kg" if k_val is not None else "Potassium: Missing",
            f"Simulated pH: {ph_val}, EC: {ec_val} dS/m" if ph_val is not None else "pH/EC: Missing",
            "Data Source: Simulated FertoBot Telemetry (Illustrative Only — Not Lab Calibrated)",
        ]

        limitations: List[str] = [
            "Simulated telemetry values are illustrative and not calibrated against physical wet-chemistry lab soil tests.",
            "Fertilizer application and crop choices must consider localized soil texture, climate, and irrigation schedule.",
        ]
        if not query_crop_detected and detected_topic not in ["crop_suitability", "ph", "ec", "npk", "rotation", "fertility", "organic", "testing"]:
            limitations.append("Crop species not specified by grower.")
        if n_val is None:
            limitations.append(f"Nitrogen sensor for {zone_id} is uncalibrated or returned missing data.")

        # 5. Formulate Topic Findings
        if detected_topic == "crop_suitability":
            matches = knowledge_output.get("suitability_matches", [])
            suitable_names = [m["crop_name"] for m in matches if m["is_suitable"]][:4]
            suit_str = ", ".join(suitable_names) if suitable_names else "Wheat, Mustard, Chickpea"
            if is_hindi:
                summary = (
                    f"वर्तमान मिट्टी रीडिंग (pH {ph_val}, नमी {moisture_val}%, EC {ec_val} dS/m) के अनुसार आपकी मिट्टी उपजाऊ और संतुलित है। "
                    f"इस मिट्टी में आप {suit_str} जैसी रबी फसलें सफलतापूर्वक उगा सकते हैं। "
                    "सर्वोत्तम सिफारिश के लिए कृपया अपने क्षेत्र का मौसम, बुवाई का मौसम (रबी/खरीफ) और सिंचाई की सुविधा बताएं।"
                )
            else:
                summary = (
                    f"Based on current soil telemetry (pH {ph_val}, Moisture {moisture_val}%, EC {ec_val} dS/m), your soil is well-balanced. "
                    f"Highly suitable crops include: {suit_str}. "
                    "For a precise recommendation, please share your geographic region, current cropping season, and irrigation method."
                )
            limitations.append("Geographic location, season, and irrigation infrastructure unconfirmed by grower.")

        elif detected_topic == "ph":
            if is_hindi:
                summary = (
                    f"मिट्टी का pH मान 6.8 एक आदर्श और तटस्थ (Neutral) स्तर है। इसका मतलब है कि मिट्टी न तो अम्लीय है और न ही क्षारीय। "
                    "इस pH पर नाइट्रोजन, फॉस्फोरस और पोटाश (NPK) सहित सभी आवश्यक सूक्ष्म पोषक तत्वों की उपलब्धता पौधों के लिए अधिकतम होती है। "
                    "यह अधिकांश फसलों (गेहूं, सरसों, चना, सब्जियां) के लिए सर्वोत्तम स्थिति है।"
                )
            else:
                summary = (
                    "A soil pH of 6.8 indicates an optimal, near-neutral condition. "
                    "At this pH level, nutrient bioavailability for Nitrogen, Phosphorus, Potassium, and key micronutrients is at its peak. "
                    "This range is ideal for almost all agricultural crops including wheat, mustard, legumes, and vegetables."
                )

        elif detected_topic == "npk":
            if is_hindi:
                summary = (
                    "नाइट्रोजन (N) और फॉस्फोरस (P) पौधों के दो अलग-अलग मुख्य पोषक तत्व हैं: "
                    "1. नाइट्रोजन (N) पौधों की वानस्पतिक वृद्धि (पत्तियां, तना और हरा रंग/क्लोरोफिल) के लिए जिम्मेदार होता है। इसकी कमी से पत्तियां पीली पड़ती हैं। "
                    "2. फॉस्फोरस (P) पौधों की जड़ों के फैलाव, ऊर्जा संचार (ATP), और फूल व बीज बनने के लिए जरूरी होता है। इसकी कमी से जड़ें कमजोर और पत्तियां बैंगनी/कांस्य रंग की हो जाती हैं।"
                )
            else:
                summary = (
                    "Nitrogen (N) and Phosphorus (P) serve distinct physiological roles: "
                    "1. Nitrogen (N) drives vegetative growth, leaf expansion, and chlorophyll production for photosynthesis. Deficiency causes generalized yellowing on older leaves. "
                    "2. Phosphorus (P) is vital for root architecture development, energy transfer (ATP synthesis), flowering, and seed formation. Deficiency results in stunted root systems and purplish leaf margins."
                )

        elif detected_topic == "ec":
            if is_hindi:
                summary = (
                    f"विद्युत चालकता (EC) मिट्टी में घुले हुए लवणों (Salinity) की मात्रा मापती है। "
                    f"वर्तमान में ज़ोन की EC {ec_val} dS/m है। 1.2 dS/m से कम EC सामान्य और गैर-खारी मानी जाती है। "
                    "यदि EC अधिक (>2.5 dS/m) हो जाए, तो मिट्टी में खारापन बढ़ जाता है जिससे जड़ों को पानी सोखने में बाधा आती है।"
                )
            else:
                summary = (
                    f"Electrical Conductivity (EC) measures the concentration of soluble salts (salinity) in soil water. "
                    f"Your current reading is {ec_val} dS/m. Values below 1.2 dS/m indicate ideal, non-saline conditions. "
                    "Elevated EC (>2.5 dS/m) exerts osmotic stress, hindering roots from absorbing water even in moist soil."
                )

        elif detected_topic == "rotation":
            if is_hindi:
                summary = (
                    "फसल चक्र (Crop Rotation) का अर्थ है एक ही खेत में लगातार एक ही फसल न उगाकर, बदल-बदल कर अलग-अलग फसलों को क्रमबद्ध उगाना। "
                    "इसके प्रमुख लाभ: 1. दलहनी फसलें (जैसे चना/मूंग) हवा से नाइट्रोजन सोखकर मिट्टी को उपजाऊ बनाती हैं। "
                    "2. कीट और फंगल बीमारियों का जीवन चक्र टूट जाता है। 3. अलग-अलग गहराई वाली जड़ें मिट्टी की संरचना सुधारती हैं।"
                )
            else:
                summary = (
                    "Crop Rotation is the agronomic practice of growing planned different crops sequentially on the same land across seasons. "
                    "Key benefits: 1. Legumes fix atmospheric nitrogen, replenishing soil fertility naturally. "
                    "2. It breaks pathogen, nematode, and insect pest lifecycles that target specific crops. "
                    "3. Alternating deep-taproot and shallow-fibrous roots improves soil aeration and nutrient utilization."
                )

        elif detected_topic == "fertility":
            if is_hindi:
                summary = (
                    "मिट्टी की उर्वरता (Soil Fertility) सुधारने के 4 मुख्य वैज्ञानिक उपाय: "
                    "1. जैविक खाद (FYM/वर्मीकम्पोस्ट) 10-12 टन प्रति हेक्टेयर डालें। "
                    "2. हरी खाद (ढैंचा या सनई) उगाकर 45 दिन बाद मिट्टी में पलटें। "
                    "3. फसल अवशेष (पराली/डंठल) जलाने के बजाय मिट्टी में मिलाएं ताकि ऑर्गेनिक कार्बन बढ़े। "
                    "4. जैव-उर्वरक (एजोटोबैक्टर, राइजोबियम, PSB) का प्रयोग करें और लैब सॉइल टेस्ट के आधार पर ही संतुलित खाद दें।"
                )
            else:
                summary = (
                    "Key agronomic methods to enhance soil fertility: "
                    "1. Incorporate 10-15 tonnes/ha of well-decomposed Farm Yard Manure (FYM) or vermicompost to boost soil organic matter. "
                    "2. Practice green manuring with Sesbania (Dhaincha) or Sunn hemp incorporated at 45 days. "
                    "3. Inoculate with bio-fertilizers (Azotobacter, Rhizobium, PSB) to mobilize nutrients. "
                    "4. Retain and mulch crop residues to enrich microbial carbon, avoiding residue burning."
                )

        elif detected_topic == "organic":
            if is_hindi:
                summary = (
                    "जैविक खेती (Organic Farming) के 4 आधारभूत सिद्धांत हैं: "
                    "1. स्वास्थ्य (Health): मिट्टी, पौधों और इंसानों के स्वास्थ्य को बिना रासायनिक जहरीले तत्वों के सुरक्षित रखना। "
                    "2. पारिस्थिकी (Ecology): प्राकृतिक पारिस्थितिकी तंत्र के साथ मिलकर काम करना। "
                    "3. निष्पक्षता (Fairness): पर्यावरण और संसाधनों का न्यायसंगत उपयोग। "
                    "4. देखभाल (Care): भावी पीढ़ियों के लिए मिट्टी और पानी का संरक्षण करना। रासायनिक खाद व कीटनाशकों के स्थान पर जीवामृत, नीम अर्क और ट्राइकोडर्मा का उपयोग किया जाता है।"
                )
            else:
                summary = (
                    "Organic Farming is guided by four international principles: "
                    "1. Principle of Health: Sustaining soil microbial life, plants, and human wellness without synthetic chemicals. "
                    "2. Principle of Ecology: Emulating living ecological cycles and recycling biological organic matter. "
                    "3. Principle of Fairness: Managing environmental resources equitably. "
                    "4. Principle of Care: Precautionary stewardship for future generations through compost, biological pest control (Trichoderma, Neem), and diverse crop rotations."
                )

        elif detected_topic == "testing":
            if is_hindi:
                summary = (
                    "हाँ, मिट्टी परीक्षण (Soil Testing) हर 2 से 3 साल में अधिकृत प्रयोगशाला से अवश्य करवानी चाहिए। "
                    "फर्तोबॉट सेंसर आपको वास्तविक समय (24/7) में नमी, तापमान और भौतिक रुझान बताते हैं, "
                    "जबकि प्रयोगशाला परीक्षण मिट्टी के कुल नाइट्रोजन, फॉस्फोरस, पोटाश, सूक्ष्म पोषक तत्वों (जिंक, लोहा) और ऑर्गेनिक कार्बन की प्रमाणित रासायनिक रिपोर्ट देता है।"
                )
            else:
                summary = (
                    "Yes, periodic laboratory soil testing is strongly recommended every 2 to 3 years. "
                    "While FertoBot IoT probes provide real-time 24/7 dynamic monitoring of soil moisture, temperature, and electrical conductivity, "
                    "accredited laboratory wet-chemistry testing provides certified baseline calibration for macro-nutrients (N, P, K), micronutrients (Zn, Fe, B), and soil organic carbon."
                )

        elif detected_symptom == "nutrient_inquiry":
            if is_hindi:
                n_str = f"{n_val} mg/kg" if n_val is not None else "उपलब्ध नहीं (सेंसर अनकैलिब्रेटेड)"
                p_str = f"{p_val} mg/kg" if p_val is not None else "अनुपलब्ध"
                k_str = f"{k_val} mg/kg" if k_val is not None else "अनुपलब्ध"
                summary = (
                    f"आपके {tel_data.get('zone_name', zone_id)} के सिमुलेटेड NPK मान हैं: "
                    f"नाइट्रोजन (N): {n_str}, फॉस्फोरस (P): {p_str}, और पोटेशियम (K): {k_str}। "
                    f"मिट्टी का pH {ph_val} और EC {ec_val} dS/m है। "
                    "कृपया ध्यान दें कि ये सिमुलेटेड डेमो रीडिंग हैं; किसी भी उर्वरक की मात्रा तय करने से पहले मिट्टी परीक्षण प्रयोगशाला से पुष्टि करें।"
                )
            else:
                n_str = f"{n_val} mg/kg" if n_val is not None else "Unavailable (Uncalibrated sensor)"
                p_str = f"{p_val} mg/kg" if p_val is not None else "Unavailable"
                k_str = f"{k_val} mg/kg" if k_val is not None else "Unavailable"
                summary = (
                    f"Simulated soil nutrient readings for {tel_data.get('zone_name', zone_id)}: "
                    f"Nitrogen (N): {n_str}, Phosphorus (P): {p_str}, and Potassium (K): {k_str}. "
                    f"Soil pH is {ph_val} and Electrical Conductivity is {ec_val} dS/m. "
                    "Note: These are illustrative demo sensor readings, not accredited lab soil test results."
                )

        elif detected_symptom == "yellow_leaves":
            n_status = "कम" if (n_val is not None and n_val < 45) else "संतुलित"
            if is_hindi:
                summary = (
                    f"टमाटर या अन्य फसलों में पत्तियों के पीले पड़ने (Chlorosis) के 4 मुख्य संभावित कारण हो सकते हैं: "
                    f"1. नाइट्रोजन की कमी: निचली पुरानी पत्तियां समान रूप से पीली पड़ जाती हैं (सिमुलेटेड N: {n_val or 'अनकैलिब्रेटेड'} mg/kg)। "
                    f"2. जलभराव या अधिक सिंचाई: नमी {moisture_val}% होने से जड़ों को ऑक्सीजन नहीं मिलती, जिससे पीलापन आता है। "
                    "3. सूक्ष्म पोषक तत्व (आयरन या जिंक) की कमी: नई ऊपरी पत्तियों की नसें हरी और बीच का हिस्सा पीला रहता है। "
                    "4. विषाणु रोग (जैसे टमाटर लीफ कर्ल): पत्तियां मुड़ती हैं और पीली चित्तीदार होती हैं। खेत में पत्तियों की स्थिति की जांच करें।"
                )
            else:
                summary = (
                    f"In tomato and other crops, leaf yellowing has four primary differential causes: "
                    f"1. Nitrogen (N) Deficiency: Older lower leaves exhibit uniform chlorosis (Simulated N: {n_val or 'uncalibrated'}). "
                    f"2. Over-irrigation / Waterlogging: Elevated moisture ({moisture_val}%) causes root hypoxia and nutrient starvation. "
                    "3. Micronutrient (Fe/Zn) Deficiency: Interveinal chlorosis on young upper foliage with green veins. "
                    "4. Viral infection (Tomato Yellow Leaf Curl): Accompanied by upward leaf curling and stunting. Inspect leaf position in field."
                )

        elif detected_crop == "wheat" and any(w in query_lower for w in ["condition", "chahiye", "requirement"]):
            c_info = knowledge_output.get("thresholds", {})
            if is_hindi:
                summary = (
                    "गेहूं (Wheat) की सफल खेती के लिए आवश्यक मिट्टी की स्थितियां: "
                    "1. मिट्टी का प्रकार: अच्छी जल निकासी वाली उपजाऊ दोमट या बलुई दोमट मिट्टी। "
                    "2. आदर्श pH: 6.0 से 7.5 के बीच (तटस्थ)। "
                    "3. नमी का स्तर: 45% से 60% (CRI व कल्ले फूटते समय नमी की कमी नहीं होनी चाहिए)। "
                    "4. तापमान: बुवाई और कल्ले फूटते समय 15°C से 22°C का ठंडा मौसम सबसे अनुकूल होता है।"
                )
            else:
                summary = (
                    "Optimal soil conditions for wheat cultivation: "
                    "1. Soil Texture: Well-drained fertile loam or clay loam with good structure. "
                    "2. Soil pH: 6.0 to 7.5 (near neutral for maximum nutrient availability). "
                    "3. Moisture: 45% to 60% root zone moisture; Crown Root Initiation (CRI at 21 days) is critical. "
                    "4. Temperature: 15°C to 25°C cool conditions during tillering and vegetative growth."
                )

        else:
            if is_hindi:
                summary = (
                    f"फसल विश्लेषण: {detected_crop or 'फसल'} के लिए वर्तमान मिट्टी का तापमान {temp_val}°C, "
                    f"नमी {moisture_val}%, और pH {ph_val} है। उचित जल निकासी और संतुलित खाद का ध्यान रखें।"
                )
            else:
                summary = (
                    f"Agronomic analysis for {detected_crop or 'crop'}: Soil temperature is {temp_val}°C, "
                    f"moisture is {moisture_val}%, and pH is {ph_val}. Ensure adequate drainage and balanced nutrition."
                )

        return AgentResult(
            agent_id=self.agent_id,
            name=self.name,
            status="completed",
            summary=summary,
            evidence=evidence,
            limitations=limitations,
            data={
                "zone_id": zone_id,
                "crop": detected_crop,
                "detected_crop": detected_crop,
                "detected_topic": detected_topic,
                "detected_symptom": detected_symptom,
                "nitrogen_mg_kg": n_val,
                "phosphorus_mg_kg": p_val,
                "potassium_mg_kg": k_val,
                "ph": ph_val,
                "electrical_conductivity_ds_m": ec_val,
                "soil_moisture_pct": moisture_val,
                "soil_temperature_c": temp_val,
                "is_simulated": True,
            },
        )
