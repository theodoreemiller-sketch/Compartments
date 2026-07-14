/**
 * Apparatus Compartment Inventory — Workbook Builder
 * ----------------------------------------------------
 * Run buildInventoryWorkbook() once from the Apps Script editor.
 * It creates a new Google Sheets workbook with ONE TAB PER VEHICLE.
 * Each tab is a rig-check checklist (Compartment → Shelf → Item) with
 * Expected Qty, Actual Qty, Status (data-validation dropdown), and Notes.
 *
 * Data was extracted from the index.html "UNOFFICIAL APPARATUS STUDY GUIDES"
 * (Glen Ellyn Fire Department probationary study material). Each apparatus
 * uses a different markup pattern in the source HTML; the parser normalized
 * everything to a single shape that this script consumes.
 *
 * NO MANUAL SETUP REQUIRED: paste this file into a new Apps Script project,
 * save, then choose "buildInventoryWorkbook" from the function dropdown and Run.
 * Authorize on first run. The new spreadsheet URL is logged to View → Logs.
 */

/* =================================================================
 * EMBEDDED INVENTORY DATA
 * Structure:  { vehicleName: { compartmentName: { shelfLabel: [itemNames] } } }
 * =================================================================
 */
const INVENTORY = {
  "Engine 60": {
    "Front — Hose Bays & Crosslays": {
      "Trash line · Crosslays · Rear skid loads · ⚠️ No front intake": [
        "100 ft Trash Line — Preconnected",
        "1¾\" Crosslays — 200 ft ×2, Both Preconnected"
      ]
    },
    "Engineer's Compartment": {
      "Left top · Right top · Middle · Bottom": [
        "Towels",
        "30-Degree Storz Adapter",
        "Pickup Tubes for Foam/Gel",
        "Reducers — Multiple Sizes",
        "Duct Tape",
        "SCBA — Self-Contained Breathing Apparatus",
        "Extra Air Bottle",
        "Foam Nozzle — 125 GPM (Orange)",
        "Chief Eductor (Foam Eductor)",
        "Gated Wye — 2½\" to (2) 1½\"",
        "Fog Nozzles ×2",
        "Rope to Move Charged 5\" Hose",
        "Adaptors — M2M, F2F, CFD, 2½\"→1¾\"",
        "Eye Protection",
        "Hydrant Bag",
        "Gate Valve",
        "30 ft of 5\" Hose",
        "Smooth Bore Nozzles"
      ]
    },
    "Middle Compartment — Driver's Side": {
      "Hand tools · Nozzles · Entry tools · Deck gun": [
        "3 Air Tanks",
        "Quartz Light (Side-Mounted)",
        "Deck Gun Ground Mount",
        "Deck Gun Nozzle",
        "Halligan Bar",
        "Halligan with Gas Turn Off",
        "Pickhead Axe / Fire Axe (×2 — Standard + Red)",
        "Flat Head Axe",
        "Sledgehammer / Maul",
        "Officer's Tool / Pry Axe",
        "K-Tool",
        "Cellar Nozzle",
        "Piercing Nozzle",
        "Fan Hanger",
        "Fire Tape"
      ]
    },
    "Rear Compartment — Driver's Side": {
      "10KW Generator · Power tools · Lighting · Ventilation fan": [
        "10KW Generator",
        "200 ft Roll of Electrical Cord",
        "B Post Cover",
        "Lights (Scene Lights)",
        "Reciprocating Saw (Sawzall)",
        "Ventilation Fan",
        "Plug Adaptors (110V Compatible)",
        "Cribbing",
        "Small Step Ladder"
      ]
    },
    "First Compartment — Officer's Side": {
      "Water rescue · Foam · Supply hose · Coping tool": [
        "Akron Coping Tool (Hose Hoist)",
        "Utility Rope — 100 ft",
        "Spare Battery",
        "Synching Rescue Collar",
        "Mustang Suit",
        "Water Helmet",
        "Water Rescue Rope",
        "Manual Pump Can (Silver Bullet)",
        "Gel Foam",
        "Oil Dry (Kitty Litter)",
        "Life Vests (×multiple)",
        "50 ft of 5\" Hose (Second Section)"
      ]
    },
    "Middle Compartment — Officer's Side": {
      "Hand tools · Forcible entry": [
        "Small Bolt Cutter",
        "Pig Tool",
        "Sledgehammer / Maul",
        "Pick Head / Fire Axe",
        "Halligan Bar (Officer Side)",
        "Flat Head Axe (Officer Side)"
      ]
    },
    "Rear Compartment — Officer's Side": {
      "Extinguishers · High Rise · Salvage · Decon": [
        "Silver Bullet — Pressurized Water",
        "ABC Dry Chemical Extinguisher",
        "CO₂ Extinguisher",
        "High Rise Pack",
        "High Rise Bag",
        "Tarps",
        "Blanket",
        "Tool Box",
        "2 Shovels — Scoop & Spade",
        "Decontamination Buckets and Soap"
      ]
    },
    "Rear of Engine": {
      "Ladders · Hurst Combi · Ram · Backboards · Hose": [
        "Hose Load Record — Clipboard",
        "10 ft Folding Ladder",
        "24 ft Extension Ladder",
        "14 ft Roof Ladder",
        "6 ft Pike Poles ×2 (Top of Ladder Compartment)",
        "2 Backboards",
        "Hurst Combi Tool — Cuts AND Spreads",
        "Ram Jam + Braces for Ram Tool",
        "Pry Tool + Pry Bar",
        "2 Shovels — Scoop & Pointed (Rear)"
      ]
    },
    "Cab Compartment": {
      "AED · Gas monitors · TIC · OB kit · Medic bag · Comms": [
        "AED — Automated External Defibrillator",
        "Medic Bag",
        "OB Kit — Obstetrics Kit",
        "2 Face Pieces — Large & Medium",
        "Extra Gloves",
        "4-Gas Monitor",
        "Gas Trac (Methane / HCN Meter)",
        "TIC — Thermal Imaging Camera",
        "Hot Stick",
        "Knox Box Key",
        "Battery Chargers",
        "Caution Tape",
        "Fire Wipes",
        "Vests",
        "Water Bottles"
      ]
    },
    "E60 Shift Rig Check — Checklist": {
      "Walk it every shift · Sign off · Own your rig": [
        "Hose Bays",
        "Engineer's Compartment",
        "Middle Compartment — Driver's Side",
        "Rear Compartment — Driver's Side",
        "First Compartment — Officer's Side",
        "Middle Compartment — Officer's Side",
        "Rear Compartment — Officer's Side",
        "Rear of Engine",
        "Cab Compartment"
      ]
    },
    "E60 Unique Items — What Makes This Rig Different": {
      "Items specific to E60 or not on all engines": [
        "E60 vs. Other Engines — Key Differences at a Glance"
      ]
    }
  },
  "Engine 61": {
    "E61 vs. E62 — Know the Differences": {
      "READ THIS FIRST — before you ever ride E61": [
        "Driver's Side Over-Wheel Compartment",
        "Air Bag Controllers — E61 vs. E62",
        "RIT Pack — E62 Only"
      ]
    },
    "Cabin Compartment & Hose Bed": {
      "Front preconnects · Side crosslays · Rear static loads": [
        "Trash Line — 100 ft, 1¾\" Preconnected",
        "1¾\" Crosslay — 200 ft, Fog Nozzle (×2)",
        "2½\" Crosslay — 200 ft, Smooth Bore Nozzle",
        "5\" Supply Hose — 30 ft (Front) + 1,000 ft (Rear Middle)",
        "Highrise Pack 150' of 1 3/4\"",
        "Storz to Steamer Adapter + Hydrant Wrench",
        "Blitz Fire — 300 ft, 3\" Preconnected"
      ]
    },
    "Compartment 1 — Engineer's Compartment": {
      "Driver's side · 3 shelves · Hose fittings, spanners, hydrant bag": [
        "Black Tool Box",
        "Airpack (SCBA)",
        "Double-Ended Spanners (×2) — Storz & Hose",
        "Wye Ball Valves — 2½\" to 1½\" (×2)",
        "Fog Nozzles (×2)",
        "Reducer Fittings — Multiple Sizes",
        "Male-to-Male & Female-to-Female Connectors",
        "Hydrant Bag"
      ]
    },
    "Compartment 2 — Hand Tools & Forcible Entry": {
      "Driver's side · Irons, pike pole, bolt cutters, K-tool": [
        "Halligan Bar (Halligan)",
        "Flat Head Axe",
        "Maul (Sledgehammer)",
        "Closet Pike Pole",
        "Bolt Cutters — Medium & Large",
        "Captain's Tool / Pry Axe (Officer's Tool)",
        "K-Tool (in Leather Case)",
        "Manhole Cover Remover",
        "Air Tanks — Outside of Comp. 2 (×3)"
      ]
    },
    "Compartment 3 — Rescue, Ventilation & Air Bags": {
      "Driver's side · Air bags · Fan · Cellar nozzle · Work lights": [
        "Cellar Nozzle on a Cellar Pipe",
        "Portable Work Lights (×2)",
        "Ventilation Fan",
        "Air Bags — 3 Bags + Yellow Control Box",
        "Cribbing",
        "Small Step Ladder",
        "Transformer Nozzles"
      ]
    },
    "Rear Middle — Extrication Equipment": {
      "Hurst tools · Hydraulic ram · Reciprocating saw · Batteries": [
        "Hurst Rescue Cutter",
        "Hurst Rescue Spreader",
        "Hydraulic Ram",
        "Reciprocating Saw",
        "Window Punch",
        "Hurst Batteries (×6) + Battery-to-AC Connector",
        "Double-Ended Spanners (×2)"
      ]
    },
    "Rear — Left Side & Backboards": {
      "New York hooks · Attic ladder · Backboards": [
        "New York Hooks — 6 ft & 8 ft",
        "Attic Ladder — 10 ft",
        "Backboards (×2)"
      ]
    },
    "Compartment 5 — Officer Side Forcible Entry & Search": {
      "Axes · Search rope · RASP · PFDs · Tool box": [
        "Pick Head Axe / Fire Axe",
        "RASP — 200 ft Search Rope",
        "Pig Drain Cover",
        "Utility Rope — 100 ft",
        "Red Bag — 4 PFDs & 1 Throw Preserver",
        "W-Tool",
        "Tool Box — General Hand Tools"
      ]
    },
    "Compartment 6 — Middle Officer / Water Rescue": {
      "Mustang suit · PFD · Ice rescue · Rope bag · Air bottles": [
        "Mustang Suit",
        "Ice Spikes & Ice Cleats",
        "Rope Throw Bag",
        "Life Safety Ring",
        "Strap with 3 Carabiners",
        "Water Helmet",
        "Air Bottles — Under Compartment (×4, 2 per side)"
      ]
    },
    "Compartment 7 — Extinguishers & Special Hazards": {
      "Silver bullet · ABC · CO2 · K-class · Fire blanket · Oil dry": [
        "Silver Bullet — Pressurized Water Extinguisher",
        "ABC Dry Chemical Extinguisher",
        "CO₂ Extinguisher",
        "Class K Extinguisher",
        "Fire Blanket — Electric Vehicle",
        "Oil Dry"
      ]
    },
    "Above Compartments — Ladders & Pike Poles": {
      "Ground ladder 24 ft · Extension ladder 14 ft · 2 pike poles": [
        "Ground Ladder — 24 ft",
        "Extension Ladder — 14 ft",
        "Pike Poles — 6 ft & 8 ft (Above Compartments)"
      ]
    },
    "Inside Cab": {
      "Medical gear · Gas monitors · Radios · ERG · Vests": [
        "Red Jump Bag — \"First In\"",
        "Green Airway Bag",
        "AED — Automated External Defibrillator (ZOLL)",
        "4-Gas Monitor (CO, O₂, H₂S, Combustible)",
        "HCN Sensor (Standalone)",
        "Hot Stick",
        "ERG — Emergency Response Guidebook",
        "Knoxbox Key",
        "Elevator Key",
        "Accountability Velcro Name Board",
        "Pet O₂ Mask",
        "Blue Lock-Out/Tag-Out Bag",
        "Dark Blue Collar Bag",
        "Small Orange Bag — Suction Unit",
        "CO₂ Meter",
        "Fire Wipes & Contractor Bags",
        "After Fire Survey Clipboard & Patient Clipboards",
        "Fire Tape & Caution Tape",
        "Red Biohazard Bags",
        "Camera",
        "FIU Investigation Box",
        "PR Box — Stickers & Public Relations Materials",
        "2 Extra SCBA Masks",
        "Binoculars",
        "Flood Light",
        "Hot Feet",
        "Blankets",
        "Vests (Under Seats)",
        "4 Portable Radios",
        "Water (Crew Hydration Supply)"
      ]
    },
    "Top of Engine": {
      "Snow shovel · Traffic cones · Fire paddle · Dawn soap": [
        "Fire Paddle",
        "Manifold for Fire Gun",
        "Dawn Soap & Brush in Bucket",
        "Traffic Cones"
      ]
    },
    "Shift Rig Check — Checklist": {
      "Walk it every shift · Sign off on it · Own your rig": [
        "Driver's Side — Cabin & Hose Bed",
        "Compartment 1 — Engineer's",
        "Compartment 2 — Hand Tools",
        "Compartment 3 — Rescue / Ventilation / Air Bags",
        "Rear Middle — Extrication",
        "Rear Left — Hooks & Ladders",
        "Compartment 5 — Officer Forcible Entry",
        "Compartment 6 — Water Rescue",
        "Compartment 7 — Extinguishers",
        "Inside Cab — Full Inventory",
        "Top of Engine"
      ]
    },
    "Quick Reference — Where Is It?": {
      "Grouped by mission · Find the right tool fast": [
        "Fire Attack — Water & Nozzles",
        "Forcible Entry",
        "Water Supply & Hydrant Connection",
        "Vehicle Extrication",
        "Water & Ice Rescue",
        "Extinguishers — Which One for Which Fire",
        "Gas Detection — Which Meter for Which Hazard",
        "Search, Overhaul & Ventilation",
        "EMS — Medical Bags at a Glance"
      ]
    },
    "E61-Specific Items — The \"Different\" List": {
      "What makes E61 unique vs. E62 · Memorize this cold": [
        "Complete E61 vs. E62 Differences — All in One Place"
      ]
    }
  },
  "Engine 62": {
    "Hose Bays — Front, Side/Middle & Rear": {
      "FRONT HOSE BAY": [
        "100 ft Trash Line — 1¾\" Preconnected",
        "30 ft 5-Inch Supply Hose (Front)",
        "Storz-to-Steamer Adapter (Front Bay)"
      ],
      "SIDE / MIDDLE HOSE BAY — CROSSLAYS": [
        "1¾\" Crosslay Preconnects ×2 — 200 ft each, Fog Nozzle",
        "2½\" Crosslay Preconnect 200 ft — Smooth Bore Nozzle"
      ],
      "REAR HOSE BAYS — OVERVIEW": [
        "Blitz Fire Line 300 ft — 3\" Preconnected",
        "Highrise Bag"
      ]
    },
    "Compartment 1 — Engineer's Compartment": {
      "TOP SHELF — MAINTENANCE & ENGINEER'S TOOLS": [
        "1\" Green Garden Hose",
        "Black Tool Box — Engineer's Maintenance Kit",
        "Top Shelf — Storz Connectors, Deck Gun / BlitzFire Nozzle, Utility Flags, Airpack"
      ],
      "MIDDLE SHELF — NOZZLES, SPANNERS & FITTINGS": [
        "Double-Ended Spanners ×2 — Storz & Hose Thread",
        "Small House Spanners with Gas Turn-Off Notch ×2",
        "Gated Wyes — 2½\" to 1½\" ×2",
        "Fog Nozzles ×2 & Smooth Bore Nozzles ×1 + yellow tip ×1",
        "Reducers & Adapters — Middle Shelf Assortment",
        "Hose Thread Connectors — 2½\" and 1¾\" Sets 6 each"
      ],
      "BOTTOM SHELF — HYDRANT BAG & 5\" HOSE": [
        "Hydrant Bag — Complete Contents"
      ]
    },
    "Compartment 2 — Irons, Forcible Entry & Air Bags": {
      "—": [
        "Halligan Bar (Haligan)",
        "Flat Head Axe",
        "Maul",
        "Closet Pike Pole (D Handle)",
        "Bolt Cutters — Medium & Large ×1 each",
        "K-Tool in Leather Case",
        "Manhole Cover Remover",
        "Air Bags — Lifting Bags ×1–2 in Comp 2",
        "Air Tanks ×3 — Outside of Comp 2"
      ]
    },
    "Compartment 3 — RIT, Rescue & Ventilation": {
      "TOP SHELF": [
        "RIT Pack — Rapid Intervention Team Pack 60-min, 4500 PSI"
      ],
      "MIDDLE SHELF": [
        "Portable Work Lights ×2",
        "Cellar Nozzle on Cellar Pipe"
      ],
      "BOTTOM SHELF": [
        "Ventilation Fan (Battery Powered, Positive Pressure Ventilation)",
        "Orange Box — Air Bag Controller",
        "Cribbing (Plastic)",
        "Transformer Nozzles"
      ]
    },
    "Rear of Truck — Left Panel, Center & Rescue Tools": {
      "LEFT OF REAR — HOOKS & LADDER": [
        "New York Hooks ×2 — 6 ft & 8 ft",
        "Attic Ladder 10 ft"
      ],
      "MIDDLE OF REAR — RESCUE TOOLS": [
        "Hurst Rescue Cutter & Hurst Rescue Spreader",
        "Hydraulic Ram",
        "Reciprocating Saw (Battery Powered)",
        "Window Punch",
        "Batteries ×6 Upper Shelf + Battery-to-AC Converter",
        "Backboards ×2 — Rear Mounted"
      ]
    },
    "Compartment 5 — Officer's Side": {
      "TOP SHELF — AXE COMPLEMENT": [
        "Pick Head Axe / Fire Axe",
        "Pig Axe"
      ],
      "MIDDLE SHELF": [
        "RASP — 200 ft Search Rope",
        "Pig Drain Cover"
      ],
      "BOTTOM SHELF": [
        "Red Bag — 4 PFDs + 1 Throw Preserver",
        "W-Tool (Hydraulic Spreading Tool)",
        "Comp 5 Tool Box — Full Contents"
      ]
    },
    "Compartment 6 — Water Rescue & Air Bottles": {
      "—": [
        "Mustang Suit",
        "Rope Throw Bag",
        "Water Helmet",
        "Life Safety Ring + Strap with 3 Carabiners",
        "Air Bottles ×4 — Under Compartment 6"
      ]
    },
    "Compartment 7 — Fire Extinguishers & Spill Control": {
      "—": [
        "Silver Bullet — Pressurized Water Extinguisher",
        "ABC Dry Chemical Extinguisher",
        "CO₂ Extinguisher",
        "Class K Extinguisher",
        "Oil Dry",
        "Fire Blanket — For Electric Vehicles"
      ]
    },
    "Above the Compartments — Ladders & Pike Poles": {
      "—": [
        "Extension Ladder 24 ft + Roof Ladder 14 ft",
        "Pike Poles ×2 — 6 ft & 8 ft (Above Compartments)"
      ]
    },
    "Inside the Cab": {
      "TOP SHELF": [
        "4-Gas CO Meter (O₂, CO, H₂S, Combustible Gas)",
        "Gas Trac (Methane Meter)",
        "HCN Sensor (Standalone)",
        "Hot Stick",
        "Blue Lockout / Tagout Bag"
      ],
      "MIDDLE SHELF — EMS BAGS": [
        "Red Jump Bag — \"First In\" EMS Bag",
        "Green Airway Bag",
        "AED — Automated External Defibrillator",
        "Small Orange Bag — Suction Device",
        "Pet O₂ Mask"
      ],
      "ALSO IN CAB — KEY ITEMS": [
        "ERG — Emergency Response Guidebook",
        "KnoxBox + Elevator Key",
        "Accountability Velcro Name Board"
      ]
    }
  },
  "Engine 63": {
    "Front of Engine": {
      "50 ft of 5\" on bumper · Gate valve + hydrant wrench on bumper · Storz to steamer": [
        "50 Feet of 5\" LDH — Front Bumper",
        "Gate Valve + Hydrant Wrench — Top of Bumper",
        "Storz-to-Steamer Adapter — Front Bumper"
      ]
    },
    "Engineer's Compartment": {
      "Top · Middle · Bottom — Fittings, hydrant bag, eductor, hose roller": [
        "Eye Protection",
        "Fog Nozzle",
        "Deck Gun Nozzle",
        "Double-Ended Spanners",
        "Gated Wye",
        "Adaptors — M2M, F2F, CFD, Reducer",
        "Storz to Steamer (Middle Shelf)",
        "Storz to 1½\"",
        "30-Degree Elbow Storz — Anti-Kink",
        "Hydrant Bag — Full Contents",
        "Chief Eductor 125 GPM (Fill Tube in Middle Container)",
        "Hose Roller",
        "5\" Hose — 25 ft (Bottom Shelf)"
      ]
    },
    "Middle Compartment — Driver's Side": {
      "Irons · Maul · K-tool · Officer's tool": [
        "Fire Axe / Pickhead Axe",
        "Flat Head Axe",
        "Sledgehammer / Maul",
        "Halligan Bar",
        "K-Tool (Added After Photos)",
        "Officer's Tool / Pry Axe (Added After Photos)"
      ]
    },
    "Rear Compartment — Driver's Side": {
      "Second Halligan · Axes · Extinguishers · Step ladder": [
        "Halligan (Rear — Second Set)",
        "Flat Head Axe (Rear)",
        "Sledgehammer + Pickhead Axe (Rear — Added Post-Photos)",
        "Silver Bullet — Pressurized Water Extinguisher",
        "Pump Can",
        "ABC Dry Chemical Extinguisher",
        "Small Step Ladder"
      ]
    },
    "First Compartment — Officer's Side": {
      "Akron coping tool · High rise bag · 50 ft of 5\"": [
        "Akron Brass Hose Hoist — Coping Tool",
        "High Rise Bag — Contents",
        "50 Feet of 5\" — Officer Side"
      ]
    },
    "Middle Compartment — Officer's Side": {
      "High rise pack · Bolt cutters": [
        "High Rise Pack",
        "Bolt Cutters"
      ]
    },
    "Rear Compartment — Officer's Side": {
      "Tool box · Cones · Tarps · Blanket · Fan hanger": [
        "Tool Box",
        "Traffic Cones",
        "Tarps",
        "Blanket",
        "Fan Hanger"
      ]
    },
    "Rear of Engine": {
      "Middle · Right side · Left side · Hose bays": [
        "Decon Bucket — Dawn Soap + Brush",
        "Garden Hose",
        "Hurst Combi Tool — Cuts AND Spreads",
        "2 Shovels — Scoop and Pointed",
        "6 ft Pike, 8 ft NY Hook, 10 ft NY Hook (Right Side)",
        "6 ft, 8 ft, 10 ft Pike Poles (Left Side)",
        "Crosslays — 200 ft 1¾\" ×2 (Top and Bottom)",
        "Skid Loads — 2½\" and 1¾\""
      ]
    },
    "Middle Compartments — Eco-Gel / Foam System": {
      "95 gpm nozzle · 95 gpm eductor · Eco-Gel · Pickup tubes · Oil Dry": [
        "95 GPM Nozzle",
        "95 GPM Eductor",
        "5-Gallon Eco-Gel Buckets — ×5",
        "Foam Aeration Tube",
        "Eductor with Pickup Tube (Second System)",
        "Foam Nozzle — 75 psi, 125 GPM",
        "Oil Dry / Kitty Litter"
      ]
    },
    "Top of Engine — Ladders": {
      "28' Extension · 16' Roof · 10' Folding": [
        "28' Extension Ladder",
        "16' Roof Ladder",
        "10' Folding Ladder"
      ]
    },
    "Cab Compartment": {
      "AED · 4-Gas · Gas Trac · HCN meter · SCBA pack · Knox Box": [
        "AED — Automated External Defibrillator",
        "4-Gas Monitor",
        "Gas Trac — Methane / HCN",
        "HCN Meter — Standalone",
        "SCBA Pack — In Cab",
        "Knox Box Key",
        "Water Bottle"
      ]
    },
    "Top of Engine": {
      "Empty water bottle · Foam/Gel · Manifold": [
        "Empty Water Bottle — Foam Operations Container",
        "Foam/Gel Supply — Top of Engine",
        "Manifold"
      ]
    },
    "E63 Shift Rig Check — Checklist": {
      "Walk it every shift · Sign off · Own your rig": [
        "Front of Engine",
        "Engineer's Compartment",
        "Middle Compartment — Driver's Side",
        "Rear Compartment — Driver's Side",
        "First Compartment — Officer's Side",
        "Middle Compartment — Officer's Side",
        "Rear Compartment — Officer's Side",
        "Middle Rear Compartment",
        "Right Side Rear",
        "Left Side Rear",
        "Rear Hose Bays",
        "Middle Compartments — Foam/Gel",
        "Ladders — Top of Engine",
        "Cab Compartment",
        "Top of Engine"
      ]
    },
    "E63 Unique Items — What Makes This Rig Different": {
      "Know this before your first shift on E63": [
        "E63 vs. Fleet — Complete Differences at a Glance"
      ]
    }
  },
  "Utility 61": {
    "Front Dash — Communications": {
      "DuCom · Fireground radio · PA system": [
        "DuCom (Gray Microphone)",
        "Fireground Microphone (Black — Lower Left)",
        "PA System Microphone (Black — Upper Right)"
      ]
    },
    "Glove Compartment": {
      "Maps · ERG · Flares · Passport · Accountability": [
        "Maps — District Street Maps",
        "Truck Loading Instruction Paper",
        "Patient Prepare Reports (Blank)",
        "Vehicle Name Laminate",
        "Spare Tire Lock Key (In Bag)",
        "Road Flares (×2)",
        "Passport Accountability System",
        "Emergency Response Guidebook (ERG)"
      ]
    },
    "Door Pockets — Driver + Officer": {
      "Roadway vests × 2": [
        "Roadway Safety Vest (×2 — One Per Door)"
      ]
    },
    "Front Bench + Back Seat": {
      "PPE · Radios": [
        "PPE — Personal Protective Equipment (Back Seat)",
        "Portable Radios (×4)"
      ]
    },
    "Truck Bed — Cases and Bins": {
      "MSA case · Milk crate · Gray bin · Water rescue · Rope": [
        "MSA Case — SCBA + Air Bottle + Face Piece (Size M)",
        "Milk Crate — Contents",
        "Gray Bin — Water Rescue Equipment",
        "Orange Square Bag — Blanket",
        "Black Bag — Flood Light + Stand",
        "Orange/Red Bag — PFD + Throw Bag",
        "Rope Spool — 200 ft",
        "ABC Fire Extinguisher",
        "Sked — Foldable Stretcher"
      ]
    },
    "Truck Bed — Tools": {
      "Pike poles · Halligan · Axes · Umbrella · Snow scraper": [
        "Pike Poles (×2)",
        "Halligan Bar",
        "Flat Head Axe",
        "Umbrella",
        "Snow Scraper"
      ]
    },
    "Supplies — Batteries & Hydration": {
      "Spare DeWalt batteries · Water bottles": [
        "Spare DeWalt Batteries",
        "Water Bottles"
      ]
    },
    "U61 Shift Rig Check — Checklist": {
      "Walk it every shift · Sign off · Own your rig": [
        "Front Dash",
        "Glove Compartment",
        "Door Pockets",
        "Front Bench + Back Seat",
        "Truck Bed — Cases & Bins",
        "Truck Bed — Tools",
        "Supplies"
      ]
    }
  },
  "Utility 62": {
    "Front Dash — Communications": {
      "Gray mic = DuCom · Black lower-left = Fireground · Black upper-right = PA": [
        "DuCom — Gray Microphone",
        "Fireground Microphone — Black, Lower Left",
        "PA System Microphone — Black, Upper Right"
      ]
    },
    "Glove Compartment": {
      "Maps · ERG · Flares · Passport · Loading guide": [
        "District Maps",
        "Truck Loading Instruction Paper",
        "Patient Prepare Reports — Blank",
        "Vehicle Name Laminate — \"Utility 62\"",
        "Spare Tire Lock Key — In Bag",
        "Road Flares — ×2",
        "Passport Accountability System",
        "Emergency Response Guidebook — ERG"
      ]
    },
    "Door Pockets — Driver + Officer": {
      "Roadway vests × 2": [
        "Roadway Safety Vests — ×2 (One Per Door)"
      ]
    },
    "Front Bench + Back Seat": {
      "PPE (sterile gloves & masks) · 4 Radios": [
        "PPE — Sterile Gloves & Masks",
        "Portable Radios — ×4"
      ]
    },
    "Truck Bed — Cases and Bins": {
      "MSA/SCBA · Milk crate · Water rescue bin · Throw bag · Rope · Extinguisher · Sked": [
        "MSA Case — SCBA + Air Bottle + Face Piece (Size M)",
        "Milk Crate — Jumper Cables, Chocks, Tape, Hitch",
        "Gray Bin — Water Rescue Equipment",
        "Orange Square Bag — Blanket",
        "Black Bag — Flood Light, Stand, Battery",
        "Orange/Red Bag — PFD + Throw Bag",
        "Rope Spool — 200 ft",
        "ABC Fire Extinguisher",
        "Sked — Foldable Rescue Stretcher"
      ]
    },
    "Truck Bed — Tools": {
      "2 Pike poles · Halligan · Flat head axe · Umbrella · Snow scraper": [
        "2 Pike Poles",
        "Halligan Bar",
        "Flat Head Axe",
        "Umbrella",
        "Snow Scraper"
      ]
    },
    "Supplies — Batteries & Hydration": {
      "Spare DeWalt batteries · Water bottles": [
        "Spare DeWalt Batteries",
        "Water Bottles"
      ]
    },
    "U62 Shift Rig Check — Checklist": {
      "Walk every section every shift · Sign off · Own your rig": [
        "Front Dash",
        "Glove Compartment",
        "Door Pockets",
        "Front Bench + Back Seat",
        "Truck Bed — Cases & Bins",
        "Truck Bed — Tools",
        "Supplies"
      ]
    }
  },
  "Brushtruck 62": {
    "Front Seat": {
      "—": [
        "Radios"
      ]
    },
    "Glove Box": {
      "—": [
        "ERG Book",
        "Bug Spray",
        "Fuel Key",
        "Water Guides / Water Source Maps"
      ]
    },
    "Back Seat": {
      "—": [
        "PFD — Personal Flotation Device",
        "Hot Stick",
        "Box Light (Large Flashlight)",
        "Hose Bag"
      ]
    },
    "Container in Back Seat": {
      "—": [
        "Small 1″ Hose",
        "Safety Vest",
        "Maps",
        "Duct Tape",
        "Caution Tape",
        "Garbage Bags",
        "Pub Ed — Public Education Materials",
        "Strap (Utility / Tie-Down)",
        "Towel"
      ]
    },
    "Rear of Vehicle — Water System": {
      "—": [
        "250-Gallon Water Tank",
        "1″ Hose Reel (200 Feet)",
        "Handle for Hose Reel",
        "Hard Suction Hose (2 × 12′ Black)",
        "Metal Filter / Strainer for Suction Hose",
        "Metal Wheel Chock (1)",
        "Plastic Gas Can (Pump Fuel)",
        "2½″ Hose Roll (50 Feet)",
        "1½″ Hose on Cross Lay (~150 Feet)",
        "Fog Nozzle"
      ]
    },
    "Rear of Vehicle — Hand Tools": {
      "—": [
        "Brush Paddles (3 Total)",
        "Pike Poles (2 Total)",
        "New York Pole / Roof Rake (1)",
        "Bolt Cutters",
        "Halligan Tool (\"Hallagan Tool\")",
        "Plastic Funnel"
      ]
    },
    "Water Pump": {
      "—": [
        "Portable Water Pump — 2½″ Inlet / 1½″ Outlet"
      ]
    },
    "Hydrant Bag": {
      "—": [
        "Gate Valve",
        "1″ Garden Hose",
        "Hydrant Wrench",
        "Small Spanner Wrench (1¾″ Hose / Gas Shut-Off)",
        "Large Spanner Wrench (5″ Hose / LDH)",
        "Storz Adapters — A through F (Hydrant Bag)",
        "Pipe Wrench",
        "Black Electrical Tape"
      ]
    }
  },
  "Squad 61": {
    "Driver's Side Front Compartment": {
      "Light Tower · Fire Investigation · Wet Vac · Particulate Mask": [
        "Light Tower Controller",
        "Fire Investigation Box",
        "Wet Vac",
        "Dust / Particulate Face Mask"
      ]
    },
    "Driver's Side Traverse — Bottom Shelf": {
      "Winch · Steering Wheel Cutter": [
        "Winch with Remote",
        "Steering Wheel Cutter"
      ]
    },
    "DS Compartment 3 (Over Wheel) — Top Shelf": {
      "Circular Saw · K12 Saw · Chainsaw · Chain Oil": [
        "Circular Saw",
        "K12 Saw",
        "Chainsaw",
        "Chain Oil"
      ]
    },
    "DS Compartment 3 (Over Wheel) — Bottom Shelf": {
      "Cordless Power Tool Set · Impacts · Grinder · Recip Saw · Blades · Bits · Charger": [
        "1/2\" Impact Wrench",
        "1/4\" Impact Driver (with Bits)",
        "Angle Grinder",
        "Reciprocating Saw (with Metal & Wood Blades)",
        "Spare Blades (Recip / Circ / Etc.)",
        "Battery Charger",
        "Drill / Driver Bits"
      ]
    },
    "Driver's Side Rear Cabinet — Air Cascade": {
      "Cascade Controls · Adapters · Towel": [
        "Cascade Controls",
        "Adapters — Air Reel, Scuba, & Boom Fill",
        "Towel"
      ]
    },
    "Officer Front Compartments": {
      "Little Giant · Tarps · Cribbing · Oil Dry · Garbage Container": [
        "Little Giant Ladder",
        "Tarps",
        "Cribbing & Chocks",
        "Oil Dry (Absorbent)",
        "Garbage Container"
      ]
    },
    "Officer's Side Traverse — Lower Shelf": {
      "Hurst Tools · Akron Lights · Jacks · Air Chisel · Chain · RIT Pack · B-Post · Punch · Wet Vac · Airbag Controller · Submersible · Road Salt": [
        "Hurst Ram Tool",
        "Hurst Cutter",
        "Hurst Spreader",
        "2× Akron Lights",
        "High Lift Jacks",
        "Traffic Cones",
        "4× Res-Q-Jacks",
        "2× Scissor Jacks",
        "Air Chisel",
        "2× Buckets of Chain",
        "RIT Airpack",
        "B-Post Tool",
        "Center Punch",
        "Wet Vac (Officer's Traverse)",
        "Airbag Controller (Older Bags)",
        "Dayton Submersible Pump",
        "Road Salt"
      ]
    },
    "Officer's Side Compartment Over Wheel": {
      "Hand Tools · Forcible Entry · Pulley System": [
        "Flat Head Axe",
        "Pick Axe",
        "Halligan",
        "Sledgehammer",
        "2× Closet Pikes",
        "Slings",
        "Pulley System"
      ]
    },
    "Officer's Side Rear Compartment": {
      "Toolboxes · Wrenches · Sockets · Cribbing · Ratchet Straps": [
        "Toolbox with SAE & Metric Wrenches",
        "Standard Toolbox",
        "Socket Sets",
        "More Cribbing & Wedges",
        "Ratchet Straps"
      ]
    },
    "Rear Compartment — \"The Big Stuff\"": {
      "Air Bags · Fire Extinguishers · Stokes · Pike Poles · Smoke Ejectors": [
        "Multi-Lift Air Bags with Controller",
        "Old Air Bag",
        "Fire Extinguishers",
        "Stokes Basket",
        "Fire Investigation Rake",
        "4× Pike Poles / NY Hooks",
        "2× Smoke Ejectors"
      ]
    },
    "Officer Coffin Compartment (Top) — Spill Gear": {
      "Pads · Oil Dry · Spill Kit · Oil Pan · Shovels": [
        "Absorbent Pads",
        "Oil Dry (Top Compartment)",
        "Spill Kit",
        "Oil Pan",
        "Shovels"
      ]
    },
    "Driver Coffin Compartment — Water Rescue Gear": {
      "Mustang Suits · Horse Collars · Helmets · Throw Bags · PFDs · Pipe Plugs": [
        "2× Mustang Suits",
        "2× Horse Collars with Water Rescue Rope",
        "2× Helmets (Water Rescue)",
        "2× Throw Bags",
        "4× PFDs (Personal Flotation Devices)",
        "Box with Pipe Plugs"
      ]
    },
    "Cab and EMS Compartment": {
      "Chargers · Hotstick · Gas Detector · AED": [
        "Spare Chargers & Batteries",
        "Hotstick",
        "Gas Track",
        "4-Gas Detector and Wand",
        "AED — Automated External Defibrillator"
      ]
    }
  }
};

/* =================================================================
 * Per-vehicle color theme used for the title bar and compartment dividers.
 * =================================================================
 */
const THEME = {
  "Engine 60": {
    "primary": "#B59410",
    "soft": "#FFF8E0"
  },
  "Engine 61": {
    "primary": "#8B1A1A",
    "soft": "#FBE4E4"
  },
  "Engine 62": {
    "primary": "#D9291A",
    "soft": "#FBE4E4"
  },
  "Engine 63": {
    "primary": "#1A4B6B",
    "soft": "#E4ECF5"
  },
  "Utility 61": {
    "primary": "#3A5AA0",
    "soft": "#E8EEF8"
  },
  "Utility 62": {
    "primary": "#E07B20",
    "soft": "#FFF4E0"
  },
  "Brushtruck 62": {
    "primary": "#3A7A3A",
    "soft": "#E8F4E8"
  },
  "Squad 61": {
    "primary": "#1A6B2A",
    "soft": "#E8F4E8"
  }
};

/* =================================================================
 * Columns shown on each sheet. Keep this in sync with writeRow_().
 * =================================================================
 */
const HEADERS = [
  'Compartment',
  'Shelf',
  'Item',
  'Expected Qty',
  'Actual Qty',
  'Status',
  'Notes / Action Required'
];

/** Acceptable values for the Status dropdown. */
const STATUS_OPTIONS = ['OK', 'Missing', 'Damaged', 'Expired', 'Out of Service', 'N/A'];

/* =================================================================
 * MAIN ENTRY POINT
 * =================================================================
 */
function buildInventoryWorkbook() {
  const stamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
  const ss = SpreadsheetApp.create('Apparatus Inventory Checklist — ' + stamp);

  // Remove the default blank "Sheet1" once we know we have other sheets to add.
  const defaultSheet = ss.getSheets()[0];

  Object.keys(INVENTORY).forEach(function (vehicle, idx) {
    const sheet = ss.insertSheet(vehicle, idx);
    buildVehicleSheet_(sheet, vehicle, INVENTORY[vehicle]);
  });

  // Clean up the default empty sheet.
  if (ss.getSheets().length > 1) {
    ss.deleteSheet(defaultSheet);
  }

  // Activate the first vehicle tab on open.
  ss.setActiveSheet(ss.getSheets()[0]);

  Logger.log('Workbook created: ' + ss.getUrl());
}

/* =================================================================
 * BUILD ONE VEHICLE SHEET
 *
 * Layout:
 *   Row 1: Title bar (merged across all columns) — "<VEHICLE> · Compartment Checklist"
 *   Row 2: Generated-on stamp + "Always verify against the actual rig" reminder
 *   Row 3: Frozen column headers
 *   Row 4+: Data rows, with a colored "section divider" row at the start of each compartment
 * =================================================================
 */
function buildVehicleSheet_(sheet, vehicle, compartments) {
  const theme = THEME[vehicle] || { primary: '#333333', soft: '#EEEEEE' };
  const NCOLS = HEADERS.length;

  // ---------- TITLE BAR ----------
  sheet.getRange(1, 1, 1, NCOLS).merge()
    .setValue(vehicle.toUpperCase() + ' · COMPARTMENT CHECKLIST')
    .setBackground(theme.primary)
    .setFontColor('#FFFFFF')
    .setFontWeight('bold')
    .setFontSize(16)
    .setHorizontalAlignment('center')
    .setVerticalAlignment('middle');
  sheet.setRowHeight(1, 36);

  // ---------- SUB-HEADER (stamp + reminder) ----------
  const stamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'EEE MMM dd yyyy');
  sheet.getRange(2, 1, 1, NCOLS).merge()
    .setValue('Generated ' + stamp + '  ·  Always verify against the actual rig before your shift.')
    .setBackground('#F2F2F2')
    .setFontColor('#444444')
    .setFontStyle('italic')
    .setHorizontalAlignment('center');

  // ---------- COLUMN HEADERS ----------
  const headerRange = sheet.getRange(3, 1, 1, NCOLS);
  headerRange.setValues([HEADERS])
    .setBackground('#222222')
    .setFontColor('#FFFFFF')
    .setFontWeight('bold')
    .setHorizontalAlignment('center');
  sheet.setFrozenRows(3);

  // ---------- DATA ROWS ----------
  let row = 4;
  let itemNumberInVehicle = 0;
  let bandedToggle = false;

  Object.keys(compartments).forEach(function (compartment) {
    const shelves = compartments[compartment];

    // Compartment section-divider row (merged, themed background)
    sheet.getRange(row, 1, 1, NCOLS).merge()
      .setValue('▸ ' + compartment.toUpperCase())
      .setBackground(theme.primary)
      .setFontColor('#FFFFFF')
      .setFontWeight('bold')
      .setHorizontalAlignment('left')
      .setVerticalAlignment('middle');
    sheet.setRowHeight(row, 26);
    row++;
    bandedToggle = false;  // reset zebra striping at the top of each compartment

    Object.keys(shelves).forEach(function (shelf) {
      const items = shelves[shelf];
      items.forEach(function (item) {
        itemNumberInVehicle++;
        const expectedQty = parseExpectedQty_(item);
        const cleanedItem = stripQuantityPrefix_(item);
        const values = [[compartment, shelf, cleanedItem, expectedQty, '', '', '']];
        const range = sheet.getRange(row, 1, 1, NCOLS);
        range.setValues(values).setVerticalAlignment('middle');

        // Alternating row shading (soft theme color vs. white)
        range.setBackground(bandedToggle ? theme.soft : '#FFFFFF');
        bandedToggle = !bandedToggle;

        // Light gray for the Compartment/Shelf cells so the eye tracks the item.
        sheet.getRange(row, 1, 1, 2).setFontColor('#5A5A5A');

        // Right-align numeric quantity columns.
        sheet.getRange(row, 4, 1, 2).setHorizontalAlignment('center');

        row++;
      });
    });
  });

  const lastDataRow = row - 1;
  const lastCol = NCOLS;

  // ---------- STATUS DROPDOWN ----------
  // Status column (index 6) gets a data-validation dropdown across all data rows.
  if (lastDataRow >= 4) {
    const statusRange = sheet.getRange(4, 6, lastDataRow - 3, 1);
    const rule = SpreadsheetApp.newDataValidation()
      .requireValueInList(STATUS_OPTIONS, true)
      .setAllowInvalid(false)
      .setHelpText('OK / Missing / Damaged / Expired / Out of Service / N/A')
      .build();
    statusRange.setDataValidation(rule);

    // Conditional formatting: color the Status cell based on value.
    const rules = sheet.getConditionalFormatRules();
    rules.push(SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('OK').setBackground('#D9EAD3').setRanges([statusRange]).build());
    rules.push(SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('Missing').setBackground('#F4CCCC').setRanges([statusRange]).build());
    rules.push(SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('Damaged').setBackground('#FCE5CD').setRanges([statusRange]).build());
    rules.push(SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('Expired').setBackground('#FCE5CD').setRanges([statusRange]).build());
    rules.push(SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('Out of Service').setBackground('#EAD1DC').setRanges([statusRange]).build());
    rules.push(SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('N/A').setBackground('#EFEFEF').setRanges([statusRange]).build());
    sheet.setConditionalFormatRules(rules);
  }

  // ---------- BORDERS, WIDTHS, WRAP ----------
  // Outer border around the data block.
  if (lastDataRow >= 3) {
    sheet.getRange(3, 1, lastDataRow - 2, lastCol)
      .setBorder(true, true, true, true, false, false, '#999999', SpreadsheetApp.BorderStyle.SOLID);
  }

  // Column widths tuned for legibility on a typical laptop screen.
  sheet.setColumnWidth(1, 230);  // Compartment
  sheet.setColumnWidth(2, 230);  // Shelf
  sheet.setColumnWidth(3, 320);  // Item
  sheet.setColumnWidth(4, 90);   // Expected Qty
  sheet.setColumnWidth(5, 90);   // Actual Qty
  sheet.setColumnWidth(6, 130);  // Status
  sheet.setColumnWidth(7, 280);  // Notes

  // Enable text wrapping on Item + Notes so long entries stay legible.
  sheet.getRange(4, 3, Math.max(1, lastDataRow - 3), 1).setWrap(true);
  sheet.getRange(4, 7, Math.max(1, lastDataRow - 3), 1).setWrap(true);

  // Footer line with the total item count for this rig.
  const footerRow = lastDataRow + 2;
  sheet.getRange(footerRow, 1, 1, NCOLS).merge()
    .setValue('Total items on ' + vehicle + ': ' + itemNumberInVehicle
              + '   ·   Mark each row, then sign and date at the bottom of your shift.')
    .setFontStyle('italic')
    .setFontColor('#666666')
    .setHorizontalAlignment('center');

  // Sign-off line.
  sheet.getRange(footerRow + 2, 1).setValue('Checked by:').setFontWeight('bold');
  sheet.getRange(footerRow + 2, 3).setValue('Date / Shift:').setFontWeight('bold');
  sheet.getRange(footerRow + 2, 5).setValue('Officer Verified:').setFontWeight('bold');

  // Hide gridlines for a cleaner check-sheet look.
  sheet.setHiddenGridlines(true);
}

/* =================================================================
 * HELPERS
 * =================================================================
 */

/**
 * Pull a leading numeric quantity out of an item name.
 *   "2× Mustang Suits"  →  2
 *   "4× PFDs"           →  4
 *   "Halligan"          →  1
 */
function parseExpectedQty_(itemName) {
  const m = itemName.match(/^(\d+)\s*[×x]\s+/i);
  if (m) return parseInt(m[1], 10);
  const m2 = itemName.match(/^(\d+)\s+/);
  if (m2) return parseInt(m2[1], 10);
  return 1;
}

/**
 * Strip the leading quantity prefix from an item name so it doesn't duplicate
 * the Expected Qty column.
 *   "2× Mustang Suits" → "Mustang Suits"
 */
function stripQuantityPrefix_(itemName) {
  return itemName.replace(/^\d+\s*[×x]\s+/i, '').replace(/^(\d+)\s+/, '').trim();
}
