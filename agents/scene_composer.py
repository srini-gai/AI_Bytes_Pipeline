"""
Scene Composer v1 — pre-render beat→action validation and scene recomposition.

Validates storyboard beats against the capability registry before rendering.
Rewrites scenes that need ComposedScene (primitive-based) rendering.
"""
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

VISUAL_ACTIONS = {
    'enter', 'exit', 'travel', 'track', 'zoom', 'split', 'merge', 'transform',
    'reveal', 'hide', 'connect', 'fill', 'drain', 'generate', 'collapse',
    'explode', 'compare', 'stamp', 'hold',
}

PRIMITIVE_ACTIONS: dict[str, set[str]] = {
    'EnterExit':       {'enter', 'exit'},
    'StampOverlay':    {'stamp', 'enter', 'reveal'},
    'ColorTransform':  {'transform'},
    'CameraTransform': {'zoom', 'track'},
    'ConnectArrow':    {'connect', 'reveal'},
    'TravelPath':      {'travel'},
    'SpatialZone':     {'reveal', 'enter', 'hold'},
    'DualLaneLayout':  {'split', 'compare'},
    'GaugeArc':        {'fill', 'drain'},
    'ObjectBlock':     {'enter', 'reveal', 'hold', 'hide'},
    'CardFan':         {'enter', 'reveal', 'hold'},
    'RibbonObject':    {'generate', 'travel', 'enter'},
}

SCENE_ACTIONS: dict[str, set[str]] = {
    'KineticTypoScene':  {'enter', 'reveal', 'hold', 'explode'},
    'TokenStreamScene':  {'generate', 'stamp', 'transform', 'reveal', 'hide', 'enter', 'exit', 'hold', 'connect', 'travel', 'fill'},
    'CTAScene':          {'enter', 'reveal', 'hold'},
    'ComposedScene':     VISUAL_ACTIONS,
}

EP03_RECOMPOSITION: dict[int, dict[str, Any]] = {
    3: {
        "component": "ComposedScene",
        "camera_overrides": {0: "slow-push-in", 1: "zoom-in", 2: "pan-follow"},
        "hero_overrides": {
            0: {"primitive": "ObjectBlock", "label": "LLM"},
            1: {"primitive": "ObjectBlock", "label": "LLM"},
            2: {"primitive": "RibbonObject"},
        },
        "data": {
            "type": "composed",
            "layers": [
                {
                    "primitive": "ObjectBlock",
                    "config": {
                        "label": "LLM",
                        "position": {"x": 540, "y": 750},
                        "width": 820, "height": 500,
                        "blockStyle": "solid",
                        "color": "#a78bfa"
                    },
                    "activeBeat": 0,
                    "zIndex": 10
                },
                {
                    "primitive": "ObjectBlock",
                    "config": {
                        "label": "Fact Checker",
                        "position": {"x": 220, "y": 340},
                        "width": 220, "height": 120,
                        "blockStyle": "crossed-out"
                    },
                    "activeBeat": 1,
                    "zIndex": 6
                },
                {
                    "primitive": "ObjectBlock",
                    "config": {
                        "label": "Truth DB",
                        "position": {"x": 540, "y": 340},
                        "width": 220, "height": 120,
                        "blockStyle": "crossed-out"
                    },
                    "activeBeat": 1,
                    "zIndex": 7
                },
                {
                    "primitive": "ObjectBlock",
                    "config": {
                        "label": "Verifier",
                        "position": {"x": 860, "y": 340},
                        "width": 220, "height": 120,
                        "blockStyle": "crossed-out"
                    },
                    "activeBeat": 1,
                    "zIndex": 8
                },
                {
                    "primitive": "StampOverlay",
                    "config": {
                        "text": "✗",
                        "target": {"x": 220, "y": 340},
                        "impact": "slam",
                        "color": "#ff3333",
                        "fontSize": 44,
                        "width": 70, "height": 70
                    },
                    "activeBeat": 1,
                    "zIndex": 9
                },
                {
                    "primitive": "StampOverlay",
                    "config": {
                        "text": "✗",
                        "target": {"x": 540, "y": 340},
                        "impact": "slam",
                        "color": "#ff3333",
                        "fontSize": 44,
                        "width": 70, "height": 70
                    },
                    "activeBeat": 1,
                    "zIndex": 9
                },
                {
                    "primitive": "StampOverlay",
                    "config": {
                        "text": "✗",
                        "target": {"x": 860, "y": 340},
                        "impact": "slam",
                        "color": "#ff3333",
                        "fontSize": 44,
                        "width": 70, "height": 70
                    },
                    "activeBeat": 1,
                    "zIndex": 9
                },
                {
                    "primitive": "RibbonObject",
                    "config": {
                        "tokens": [
                            {"text": "the", "color": "#ffffff"},
                            {"text": "most", "color": "#ffffff"},
                            {"text": "likely", "color": "#ffffff"},
                            {"text": "next", "color": "#a78bfa"}
                        ],
                        "startPos": {"x": 60, "y": 1200},
                        "endPos": {"x": 1020, "y": 1200},
                        "showConnector": True,
                        "tokenSize": 110
                    },
                    "activeBeat": 2,
                    "zIndex": 18
                }
            ]
        }
    },
    4: {
        "component": "ComposedScene",
        "camera_overrides": {0: "pan-follow", 1: "pan-follow", 2: "slow-push-in", 3: "static"},
        "hero_overrides": {
            0: {"primitive": "RibbonObject"},
            1: {"primitive": "RibbonObject"},
            2: {"primitive": "ObjectBlock", "label": "OUTPUT"},
            3: {"primitive": "StampOverlay", "label": "HALLUCINATION"},
        },
        "data": {
            "type": "composed",
            "layers": [
                {
                    "primitive": "CameraTransform",
                    "config": {
                        "operation": "pan-follow",
                        "intensity": 0.9
                    },
                    "activeBeat": 0,
                    "zIndex": 0
                },
                {
                    "primitive": "SpatialZone",
                    "config": {
                        "bounds": {"x": 190, "y": 400, "width": 700, "height": 260},
                        "label": "SPARSE DATA",
                        "borderStyle": "glow",
                        "color": "#ff3333",
                        "pulse": True
                    },
                    "activeBeat": 0,
                    "zIndex": 2
                },
                {
                    "primitive": "RibbonObject",
                    "config": {
                        "tokens": [
                            {"text": "the", "color": "#ffffff"},
                            {"text": "data", "color": "#ffffff"},
                            {"text": "shows", "color": "#ffffff"}
                        ],
                        "startPos": {"x": 60, "y": 700},
                        "endPos": {"x": 1020, "y": 700},
                        "showConnector": True,
                        "tokenSize": 170
                    },
                    "activeBeat": 0,
                    "zIndex": 8
                },
                {
                    "primitive": "RibbonObject",
                    "config": {
                        "tokens": [
                            {"text": "that", "color": "#ff3333", "fabricated": True},
                            {"text": "the", "color": "#ff3333", "fabricated": True},
                            {"text": "study", "color": "#ff3333", "fabricated": True}
                        ],
                        "startPos": {"x": 300, "y": 700},
                        "endPos": {"x": 1020, "y": 700},
                        "showConnector": False,
                        "tokenSize": 170
                    },
                    "activeBeat": 1,
                    "zIndex": 7
                },
                {
                    "primitive": "ObjectBlock",
                    "config": {
                        "label": "OUTPUT",
                        "position": {"x": 540, "y": 1150},
                        "width": 750, "height": 400,
                        "blockStyle": "solid",
                        "color": "#ffffff"
                    },
                    "activeBeat": 2,
                    "zIndex": 10
                },
                {
                    "primitive": "StampOverlay",
                    "config": {
                        "text": "HALLUCINATION",
                        "target": {"x": 540, "y": 1150},
                        "impact": "slam",
                        "color": "#ff3333",
                        "fontSize": 60,
                        "width": 900, "height": 220
                    },
                    "activeBeat": 3,
                    "zIndex": 20
                }
            ]
        }
    },
    5: {
        "component": "ComposedScene",
        "camera_overrides": {0: "slow-push-in", 1: "static", 2: "static"},
        "data": {
            "type": "composed",
            "layers": [
                {
                    "primitive": "CardFan",
                    "config": {
                        "cards": [
                            {"label": "Research Paper", "sublabel": "Dr. A. Thompson et al.", "icon": "📝"},
                            {"label": "Legal Case", "sublabel": "Smith v. United 2019", "icon": "⚖️"},
                            {"label": "Drug Interaction", "sublabel": "Warfarin + Aspirin", "icon": "💊"}
                        ],
                        "origin": {"x": 540, "y": 800},
                        "spreadAngle": 15,
                        "holdAll": True
                    },
                    "activeBeat": 0,
                    "zIndex": 10
                },
                {
                    "primitive": "StampOverlay",
                    "config": {
                        "text": "FABRICATED",
                        "target": {"x": 380, "y": 750},
                        "impact": "slam",
                        "color": "#ff3333",
                        "angle": -15,
                        "fontSize": 64
                    },
                    "activeBeat": 1,
                    "zIndex": 14
                },
                {
                    "primitive": "StampOverlay",
                    "config": {
                        "text": "FABRICATED",
                        "target": {"x": 700, "y": 750},
                        "impact": "slam",
                        "color": "#ff3333",
                        "angle": -15,
                        "fontSize": 64
                    },
                    "activeBeat": 1,
                    "zIndex": 15
                },
                {
                    "primitive": "StampOverlay",
                    "config": {
                        "text": "FABRICATED",
                        "target": {"x": 540, "y": 800},
                        "impact": "slam",
                        "color": "#ff3333",
                        "angle": -15,
                        "fontSize": 64
                    },
                    "activeBeat": 2,
                    "zIndex": 16
                }
            ]
        }
    },
    6: {
        "component": "ComposedScene",
        "camera_overrides": {0: "slow-push-in", 1: "zoom-in", 2: "static"},
        "hero_overrides": {
            0: {"primitive": "GaugeArc"},
            1: {"primitive": "StampOverlay", "label": "DANGER ZONE"},
            2: {"primitive": "StampOverlay", "label": "HALLUCINATED CLAIM"},
        },
        "data": {
            "type": "composed",
            "layers": [
                {
                    "primitive": "GaugeArc",
                    "config": {
                        "center": {"x": 540, "y": 700},
                        "radius": 280,
                        "targetValue": 1.0,
                        "fillColor": "#ff3333",
                        "zones": [
                            {"start": 0.0, "end": 0.5, "color": "#34d399"},
                            {"start": 0.5, "end": 0.8, "color": "#facc15"},
                            {"start": 0.8, "end": 1.0, "color": "#ff3333", "label": "DANGER ZONE"}
                        ],
                        "title": "CONFIDENCE",
                        "valueLabel": "100%",
                        "pulse": True
                    },
                    "activeBeat": 0,
                    "zIndex": 6
                },
                {
                    "primitive": "StampOverlay",
                    "config": {
                        "text": "DANGER ZONE",
                        "target": {"x": 540, "y": 1100},
                        "impact": "slam",
                        "color": "#ff3333",
                        "fontSize": 64,
                        "width": 780, "height": 200
                    },
                    "activeBeat": 1,
                    "zIndex": 10
                },
                {
                    "primitive": "StampOverlay",
                    "config": {
                        "text": "HALLUCINATED CLAIM",
                        "target": {"x": 540, "y": 1350},
                        "impact": "slam",
                        "color": "#ff3333",
                        "fontSize": 56,
                        "width": 900, "height": 200
                    },
                    "activeBeat": 2,
                    "zIndex": 14
                }
            ]
        }
    },
    7: {
        "component": "ComposedScene",
        "camera_overrides": {0: "slow-push-in", 1: "zoom-in", 2: "pan-follow", 3: "zoom-out"},
        "hero_overrides": {
            0: {"primitive": "EnterExit", "label": "Hallucinated Output"},
            1: {"primitive": "EnterExit", "label": "Hallucinated Output"},
            2: {"primitive": "TravelPath", "label": "Documents"},
            3: {"primitive": "ObjectBlock", "label": "Grounded Output"},
        },
        "data": {
            "type": "composed",
            "layers": [
                {
                    "primitive": "CameraTransform",
                    "config": {
                        "operation": "slow-push-in",
                        "intensity": 0.4
                    },
                    "activeBeat": 0,
                    "zIndex": 0
                },
                {
                    "primitive": "EnterExit",
                    "config": {
                        "children": "Hallucinated Output",
                        "position": {"x": 540, "y": 650},
                        "color": "#ff3333",
                        "fontSize": 48,
                        "width": 700,
                        "height": 350,
                        "enterStyle": "scale",
                        "exitStyle": "fade",
                        "exitBeatIndex": 2
                    },
                    "activeBeat": 0,
                    "zIndex": 11
                },
                {
                    "primitive": "EnterExit",
                    "config": {
                        "children": "UNVERIFIED",
                        "position": {"x": 540, "y": 950},
                        "color": "#ff3333",
                        "fontSize": 40,
                        "width": 500,
                        "height": 180,
                        "enterStyle": "slam",
                        "exitStyle": "fade",
                        "exitBeatIndex": 2
                    },
                    "activeBeat": 1,
                    "zIndex": 10
                },
                {
                    "primitive": "TravelPath",
                    "config": {
                        "label": "Documents → LLM",
                        "from": {"x": 80, "y": 1300},
                        "to": {"x": 1000, "y": 1300},
                        "objectWidth": 800,
                        "objectHeight": 220,
                        "color": "#34d399",
                        "style": "animated"
                    },
                    "activeBeat": 2,
                    "zIndex": 15
                },
                {
                    "primitive": "ObjectBlock",
                    "config": {
                        "label": "Grounded Output",
                        "position": {"x": 540, "y": 1350},
                        "width": 800, "height": 500,
                        "blockStyle": "solid",
                        "color": "#34d399"
                    },
                    "activeBeat": 3,
                    "zIndex": 16
                },
                {
                    "primitive": "RibbonObject",
                    "config": {
                        "tokens": [
                            {"text": "grounded", "color": "#34d399"},
                            {"text": "verified", "color": "#34d399"},
                            {"text": "output", "color": "#ffffff"}
                        ],
                        "startPos": {"x": 200, "y": 1700},
                        "endPos": {"x": 900, "y": 1700},
                        "showConnector": True,
                        "tokenSize": 50
                    },
                    "activeBeat": 3,
                    "zIndex": 14
                },
                {
                    "primitive": "StampOverlay",
                    "config": {
                        "text": "✓",
                        "target": {"x": 540, "y": 1350},
                        "impact": "fade",
                        "color": "#34d399",
                        "fontSize": 64,
                        "width": 120, "height": 120
                    },
                    "activeBeat": 3,
                    "zIndex": 15
                }
            ]
        }
    },
    8: {
        "component": "ComposedScene",
        "camera_overrides": {0: "pan-follow", 1: "static", 2: "focus-shift"},
        "hero_overrides": {
            0: {"primitive": "RibbonObject"},
            1: {"primitive": "StampOverlay", "label": "PREDICT ≠ VERIFY"},
            2: {"primitive": "RibbonObject"},
        },
        "data": {
            "type": "composed",
            "layers": [
                {
                    "primitive": "ObjectBlock",
                    "config": {
                        "label": "grounded",
                        "position": {"x": 540, "y": 600},
                        "width": 800, "height": 350,
                        "blockStyle": "solid",
                        "color": "#34d399"
                    },
                    "activeBeat": 0,
                    "zIndex": 4
                },
                {
                    "primitive": "RibbonObject",
                    "config": {
                        "tokens": [
                            {"text": "grounded", "color": "#34d399"},
                            {"text": "verified", "color": "#34d399"},
                            {"text": "output", "color": "#ffffff"}
                        ],
                        "startPos": {"x": 80, "y": 600},
                        "endPos": {"x": 750, "y": 600},
                        "showConnector": False,
                        "tokenSize": 140
                    },
                    "activeBeat": 0,
                    "zIndex": 6
                },
                {
                    "primitive": "StampOverlay",
                    "config": {
                        "text": "PREDICT ≠ VERIFY",
                        "target": {"x": 540, "y": 960},
                        "impact": "slam",
                        "color": "#ff3333",
                        "fontSize": 72,
                        "width": 900, "height": 200
                    },
                    "activeBeat": 1,
                    "zIndex": 14
                },
                {
                    "primitive": "EnterExit",
                    "config": {
                        "enterStyle": "fade",
                        "children": "AI predicts text. Never verifies truth.",
                        "position": {"x": 540, "y": 1200},
                        "color": "#ffffff",
                        "fontSize": 28
                    },
                    "activeBeat": 2,
                    "zIndex": 12
                },
                {
                    "primitive": "RibbonObject",
                    "config": {
                        "tokens": [
                            {"text": "grounded", "color": "#ffffff"},
                            {"text": "verified", "color": "#ffffff"},
                            {"text": "truth", "color": "#34d399"}
                        ],
                        "startPos": {"x": 100, "y": 600},
                        "endPos": {"x": 900, "y": 600},
                        "showConnector": False,
                        "tokenSize": 135
                    },
                    "activeBeat": 2,
                    "zIndex": 20
                }
            ]
        }
    }
}


def extract_actions_from_beat(beat: dict[str, Any]) -> set[str]:
    """Extract visual action verbs from a beat's action description.

    Uses word-boundary matching and contextual rules to avoid false
    positives from descriptive language (e.g. 'slams' != 'stamp').
    """
    import re
    action_text = beat.get("action", "").lower()
    found: set[str] = set()

    WORD_ACTIONS = {
        'enter', 'exit', 'travel', 'track', 'zoom', 'split', 'merge',
        'transform', 'reveal', 'hide', 'connect', 'fill', 'drain',
        'generate', 'collapse', 'explode', 'compare', 'stamp', 'hold',
    }

    for va in WORD_ACTIONS:
        if re.search(rf'\b{va}(s|ed|ing|es)?\b', action_text):
            found.add(va)

    if re.search(r'\bstamp(s|ed)?\b', action_text):
        found.add('stamp')
    if re.search(r'\b(fan|card).*(out|in|reveal|enter)', action_text):
        found.add('enter')
    if re.search(r'\bdrift', action_text):
        found.add('travel')
    if re.search(r'\b(dial|gauge)\b', action_text) or re.search(r'\bfill(s|ed|ing)?\b', action_text):
        found.add('fill')
    if re.search(r'\barrow\b', action_text) and 'connect' not in found:
        found.add('connect')
    if re.search(r'\blane\b', action_text) and 'split' not in found:
        found.add('split')
    if re.search(r'\b(pulse|lock)\b', action_text):
        found.add('hold')
    if re.search(r'\b(peel|layer)\b', action_text):
        found.add('reveal')
    if re.search(r'\bflow(s|ed|ing)?\b', action_text):
        found.add('generate')
    if re.search(r'\bbounce', action_text):
        found.add('enter')
    if re.search(r'\bsnap', action_text):
        found.add('reveal')
    if re.search(r'\bdim(s|med)?\b', action_text):
        found.add('hide')
    if re.search(r'\bbypass', action_text):
        found.add('travel')
    if re.search(r'\bestablish', action_text):
        found.add('enter')

    if not found:
        found.add('hold')
    return found


def validate_beat_coverage(storyboard: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate every beat's required actions against component capabilities."""
    results: list[dict[str, Any]] = []
    total_beats = 0
    covered_beats = 0

    for scene in storyboard:
        sid = scene["scene_id"]
        component = scene["component"]
        beats = scene.get("beats", [])

        if component in SCENE_ACTIONS:
            supported = SCENE_ACTIONS[component]
        else:
            supported = set()

        for bi, beat in enumerate(beats):
            total_beats += 1
            required = extract_actions_from_beat(beat)
            missing = required - supported
            is_covered = len(missing) == 0
            if is_covered:
                covered_beats += 1

            results.append({
                "scene_id": sid,
                "beat_index": bi,
                "component": component,
                "required_actions": sorted(required),
                "supported_actions": sorted(supported),
                "missing_actions": sorted(missing),
                "covered": is_covered,
                "beat_action": beat.get("action", "")[:80],
            })

    return {
        "total_beats": total_beats,
        "covered_beats": covered_beats,
        "coverage": f"{covered_beats}/{total_beats}",
        "all_covered": covered_beats == total_beats,
        "beats": results,
    }


def recompose_storyboard(storyboard: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply EP03 recomposition: replace S03-S08 components with ComposedScene."""
    recomposed = []
    for scene in storyboard:
        sid = scene["scene_id"]
        if sid in EP03_RECOMPOSITION:
            new_scene = {**scene}
            recomp = EP03_RECOMPOSITION[sid]
            new_scene["component"] = recomp["component"]
            new_scene["data"] = recomp["data"]
            if "hero_overrides" in recomp:
                new_scene["hero_overrides"] = recomp["hero_overrides"]
            cam_overrides = recomp.get("camera_overrides", {})
            if cam_overrides:
                beats = list(new_scene.get("beats", []))
                for bi, cam in cam_overrides.items():
                    idx = int(bi)
                    if idx < len(beats):
                        beats[idx] = {**beats[idx], "camera": cam}
                new_scene["beats"] = beats
            recomposed.append(new_scene)
        else:
            recomposed.append(scene)
    return recomposed


# ── Composition Quality Layer ───────────────────────────────────────────────

FRAME_W = 1080
FRAME_H = 1920

COMPOSITION_RULES: list[dict[str, str]] = [
    {"id": "R01", "name": "hero_exists",
     "desc": "Every beat must have exactly one hero_object"},
    {"id": "R02", "name": "hero_dominance",
     "desc": "Primitive-aware: ObjectBlock w>=40%|h>=18%|area>=10%; Ribbon w>=60%+h>=7%; Stamp w>=65%|h>=10%; CardFan area>=25%"},
    {"id": "R03", "name": "element_count",
     "desc": "No more than 5 simultaneously visible elements per beat"},
    {"id": "R04", "name": "z_hierarchy",
     "desc": "Hero above all supporting semantic objects; only StampOverlay above when stamp is primary action"},
    {"id": "R05", "name": "camera_matches_intent",
     "desc": "Camera motion must match beat emphasis (zoom-in for reveal, static for hold)"},
    {"id": "R06", "name": "entry_visible",
     "desc": "Hero entry_action must use an animated primitive (not instant appear)"},
    {"id": "R07", "name": "state_change",
     "desc": "result_state must differ from entry state (something must change)"},
    {"id": "R08", "name": "continuity",
     "desc": "Cross-scene continuity: declared continuity objects must hand off at scene boundaries"},
    {"id": "R09", "name": "environment_subdued",
     "desc": "Structural env (DualLane/SpatialZone) visually subordinate unless beat makes it the semantic subject"},
    {"id": "R10", "name": "no_orphan_layers",
     "desc": "Every layer must be active in at least one beat of its scene"},
]

# Primitives excluded from hero candidacy (environment/layout)
HERO_EXCLUDED = {'CameraTransform', 'ColorTransform'}

# Structural environment primitives (may dominate area but not hero unless semantic subject)
STRUCTURAL_ENV = {'DualLaneLayout', 'SpatialZone', 'CameraTransform'}

# EP03 declared continuity object and required handoff scenes
EP03_CONTINUITY = {
    "object": "RibbonObject",
    "handoffs": [(3, 4), (7, 8)],
}

# Animated entry styles that count as visible entry
ANIMATED_ENTRIES = {'slam', 'scale', 'fade', 'slide', 'enter', 'reveal', 'fan', 'fill', 'travel'}

# Camera→intent alignment map (user-specified mapping)
CAMERA_INTENT_MAP: dict[str, set[str]] = {
    'static': {'hold', 'compare', 'stamp'},
    'zoom-in': {'reveal', 'stamp', 'focus', 'fill'},
    'zoom-out': {'hold', 'compare', 'reveal', 'exit'},
    'slow-push-in': {'reveal', 'fill', 'enter', 'hold'},
    'pan-follow': {'travel', 'generate', 'connect', 'enter'},
    'pan-right': {'travel', 'connect', 'exit'},
    'focus-shift': {'reveal', 'compare', 'transform'},
}


def _estimate_layer_area(layer: dict[str, Any]) -> float:
    """Estimate the frame-area fraction a layer occupies (0.0–1.0)."""
    config = layer.get("config", {})
    prim = layer.get("primitive", "")
    total = FRAME_W * FRAME_H

    if prim == "ObjectBlock":
        w = config.get("width", 200)
        h = config.get("height", 100)
        return (w * h) / total

    if prim == "StampOverlay":
        w = config.get("width", 100)
        h = config.get("height", 60)
        fs = config.get("fontSize", 36)
        text = config.get("text", "X")
        text_w = len(text) * fs * 0.7
        return max(w * h, text_w * fs) / total

    if prim == "GaugeArc":
        r = config.get("radius", 200)
        return (3.14159 * r * r) / total

    if prim == "SpatialZone":
        bounds = config.get("bounds", {})
        w = bounds.get("width", 400)
        h = bounds.get("height", 400)
        return (w * h) / total

    if prim == "DualLaneLayout":
        return 0.85

    if prim == "CardFan":
        cards = config.get("cards", [])
        return min(0.5, len(cards) * 0.12)

    if prim == "RibbonObject":
        sp = config.get("startPos", {"x": 0})
        ep = config.get("endPos", {"x": FRAME_W})
        ribbon_w = abs(ep.get("x", FRAME_W) - sp.get("x", 0))
        ts = config.get("tokenSize", 36)
        return (ribbon_w * ts * 2) / total

    if prim == "ConnectArrow":
        return 0.03

    if prim == "TravelPath":
        ow = config.get("objectWidth", config.get("width", 200))
        oh = config.get("objectHeight", config.get("height", 100))
        return (ow * oh) / total

    if prim == "EnterExit":
        fs = config.get("fontSize", 28)
        text = config.get("children", "")
        return (len(text) * fs * 0.6 * fs) / total

    if prim == "CameraTransform":
        return 0.0

    if prim == "ColorTransform":
        return 0.0

    return 0.05


def _estimate_layer_width(layer: dict[str, Any]) -> float:
    """Estimate the pixel width a layer occupies."""
    config = layer.get("config", {})
    prim = layer.get("primitive", "")
    if prim == "ObjectBlock":
        return config.get("width", 200)
    if prim == "GaugeArc":
        return config.get("radius", 200) * 2
    if prim == "RibbonObject":
        sp = config.get("startPos", {"x": 0})
        ep = config.get("endPos", {"x": FRAME_W})
        return abs(ep.get("x", FRAME_W) - sp.get("x", 0))
    if prim == "CardFan":
        return FRAME_W * 0.7
    if prim == "SpatialZone":
        return config.get("bounds", {}).get("width", 400)
    if prim == "DualLaneLayout":
        return FRAME_W
    if prim == "EnterExit":
        fs = config.get("fontSize", 28)
        text = config.get("children", "")
        return len(text) * fs * 0.6
    if prim == "StampOverlay":
        fs = config.get("fontSize", 36)
        text = config.get("text", "X")
        return max(config.get("width", 100), len(text) * fs * 0.7)
    if prim == "TravelPath":
        return config.get("objectWidth", config.get("width", 200))
    return config.get("width", 100)


def _estimate_layer_height(layer: dict[str, Any]) -> float:
    """Estimate the pixel height a layer occupies."""
    config = layer.get("config", {})
    prim = layer.get("primitive", "")
    if prim == "ObjectBlock":
        return config.get("height", 100)
    if prim == "GaugeArc":
        return config.get("radius", 200) * 2
    if prim == "RibbonObject":
        return config.get("tokenSize", 36) * 2
    if prim == "CardFan":
        cards = config.get("cards", [])
        return min(0.5, len(cards) * 0.12) * FRAME_H
    if prim == "SpatialZone":
        return config.get("bounds", {}).get("height", 400)
    if prim == "DualLaneLayout":
        return FRAME_H
    if prim == "EnterExit":
        return config.get("fontSize", 28)
    if prim == "StampOverlay":
        return max(config.get("height", 60), config.get("fontSize", 36))
    if prim == "ConnectArrow":
        return 30
    if prim == "TravelPath":
        return config.get("objectHeight", 50)
    return config.get("height", 100)


def _check_hero_dominance(
    hero: dict[str, Any],
    hero_area: float,
    camera: str,
    action_text: str,
) -> tuple[bool, str]:
    """Primitive-aware hero dominance check (R02).

    Returns (passes, reason_if_fail).
    """
    prim = hero.get("primitive", "")
    w_px = _estimate_layer_width(hero)
    h_px = _estimate_layer_height(hero)
    w_frac = w_px / FRAME_W
    h_frac = h_px / FRAME_H

    if prim in ("ObjectBlock", "GaugeArc"):
        if w_frac >= 0.40:
            return True, ""
        if h_frac >= 0.18:
            return True, ""
        if hero_area >= 0.10:
            return True, ""
        return False, (
            f"ObjectBlock/Gauge hero '{hero.get('config', {}).get('label', '?')}' "
            f"w={w_frac*100:.0f}%<40%, h={h_frac*100:.0f}%<18%, area={hero_area*100:.1f}%<10%"
        )

    if prim in ("RibbonObject", "TravelPath"):
        if w_frac >= 0.60 and h_frac >= 0.07:
            return True, ""
        if camera in ("pan-follow", "zoom-in", "slow-push-in"):
            if w_frac >= 0.60:
                return True, ""
        return False, (
            f"Ribbon/Travel hero w={w_frac*100:.0f}%, h={h_frac*100:.1f}% "
            f"(need w>=60%+h>=7%, or w>=60%+camera-follow)"
        )

    if prim == "StampOverlay":
        if w_frac >= 0.65:
            return True, ""
        if h_frac >= 0.10:
            return True, ""
        return False, (
            f"Stamp hero '{hero.get('config', {}).get('text', '?')}' "
            f"w={w_frac*100:.0f}%<65%, h={h_frac*100:.1f}%<10%"
        )

    if prim == "CardFan":
        if hero_area >= 0.25:
            return True, ""
        return False, f"CardFan hero area={hero_area*100:.1f}%<25%"

    if prim == "SpatialZone":
        if w_frac >= 0.40 or h_frac >= 0.18 or hero_area >= 0.10:
            return True, ""
        return False, (
            f"SpatialZone hero w={w_frac*100:.0f}%, h={h_frac*100:.0f}%, "
            f"area={hero_area*100:.1f}% — none meets threshold"
        )

    if prim == "EnterExit":
        child_text = hero.get("config", {}).get("children", "")
        fs = hero.get("config", {}).get("fontSize", 28)
        effective_w = len(child_text) * fs * 0.6
        effective_w_frac = effective_w / FRAME_W
        effective_h_frac = fs / FRAME_H
        if effective_w_frac >= 0.40 or effective_h_frac >= 0.04:
            return True, ""
        return False, (
            f"EnterExit hero '{child_text}' "
            f"w={effective_w_frac*100:.0f}%, h={effective_h_frac*100:.1f}% — "
            f"evaluate semantic child, not wrapper"
        )

    if prim == "ConnectArrow":
        return False, f"ConnectArrow cannot be a dominant hero (area={hero_area*100:.1f}%)"

    if w_frac >= 0.40 or h_frac >= 0.18 or hero_area >= 0.10:
        return True, ""
    return False, (
        f"Hero '{prim}' w={w_frac*100:.0f}%, h={h_frac*100:.0f}%, "
        f"area={hero_area*100:.1f}% — below primitive-aware threshold"
    )


def _layer_entry_style(layer: dict[str, Any]) -> str:
    """Determine how a layer enters the frame."""
    config = layer.get("config", {})
    prim = layer.get("primitive", "")

    if prim == "EnterExit":
        return config.get("enterStyle", "fade")
    if prim == "StampOverlay":
        return config.get("impact", "slam")
    if prim == "CardFan":
        return "fan"
    if prim == "GaugeArc":
        return "fill"
    if prim == "RibbonObject":
        return "travel"
    if prim == "TravelPath":
        return "travel"
    if prim == "ConnectArrow":
        return "reveal"
    if prim == "ObjectBlock":
        return "enter"
    if prim == "SpatialZone":
        return "reveal"
    if prim == "DualLaneLayout":
        return "reveal"
    if prim == "CameraTransform":
        return "hold"
    return "enter"


def analyze_beat_composition(
    scene: dict[str, Any],
    beat_idx: int,
    beat: dict[str, Any],
    prev_beat_result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Analyze a single beat's visual composition against quality rules."""
    data = scene.get("data", {})
    layers = data.get("layers", []) if isinstance(data, dict) else []
    component = scene.get("component", "")
    sid = scene.get("scene_id", 0)
    camera = beat.get("camera", "static")
    focus = beat.get("focus", "")
    action_text = beat.get("action", "").lower()

    # Active layers at this beat
    active_layers = [
        l for l in layers if l.get("activeBeat", 0) <= beat_idx
    ]

    # Newly entering layers
    entering_layers = [
        l for l in layers if l.get("activeBeat", 0) == beat_idx
    ]

    # Estimate areas
    layer_areas: list[tuple[dict[str, Any], float]] = [
        (l, _estimate_layer_area(l)) for l in active_layers
        if l.get("primitive") not in ("CameraTransform", "ColorTransform")
    ]
    layer_areas.sort(key=lambda x: x[1], reverse=True)

    # Determine hero_object — declared-first, then hybrid fallback:
    # 0. If scene declares a hero_override for this beat, use it
    # 1. Start with largest active non-structural-env element
    # 2. Entering content claims hero if area ≥ 50% of largest active
    # 3. Stamps claim hero if area ≥ 80% of current hero
    # DualLaneLayout/SpatialZone are structural env — not hero unless semantic subject
    hero = None
    hero_area = 0.0
    declared_hero = False

    # Step 0: check for declared semantic hero override
    hero_overrides = scene.get("hero_overrides", {})
    override_spec = hero_overrides.get(beat_idx) or hero_overrides.get(str(beat_idx))
    if override_spec:
        o_prim = override_spec.get("primitive", "")
        o_label = override_spec.get("label", "")
        for l, a in layer_areas:
            lp = l.get("primitive", "")
            ll = l.get("config", {}).get("label") or l.get("config", {}).get("text") or l.get("config", {}).get("children", "")
            if lp == o_prim and (not o_label or o_label in ll):
                hero, hero_area = l, a
                declared_hero = True
                break

    if not declared_hero:
        # Step 1: largest active non-structural-env element
        non_env_areas = [
            (l, a) for l, a in layer_areas
            if l.get("primitive") not in STRUCTURAL_ENV
        ]
        if non_env_areas:
            hero, hero_area = non_env_areas[0]

        # Step 2: entering content claims hero if ≥ 50% of largest active area
        if entering_layers and hero_area > 0:
            entering_areas = [
                (l, _estimate_layer_area(l)) for l in entering_layers
                if l.get("primitive") not in STRUCTURAL_ENV
            ]
            if entering_areas:
                entering_areas.sort(key=lambda x: x[1], reverse=True)
                best_entering, best_entering_area = entering_areas[0]
                if best_entering_area >= hero_area * 0.5:
                    hero, hero_area = best_entering, best_entering_area
        elif entering_layers and hero is None:
            entering_areas = [
                (l, _estimate_layer_area(l)) for l in entering_layers
                if l.get("primitive") not in STRUCTURAL_ENV
            ]
            if entering_areas:
                entering_areas.sort(key=lambda x: x[1], reverse=True)
                hero, hero_area = entering_areas[0]

        # Step 3: stamp claims hero if stamp area ≥ 80% of current hero area
        if hero and hero.get("primitive") != "StampOverlay":
            stamp_layers = [
                (l, _estimate_layer_area(l)) for l in entering_layers
                if l.get("primitive") == "StampOverlay"
            ]
            if stamp_layers:
                stamp_layers.sort(key=lambda x: x[1], reverse=True)
                best_stamp, best_stamp_area = stamp_layers[0]
                if best_stamp_area >= hero_area * 0.8:
                    hero, hero_area = best_stamp, best_stamp_area

    hero_label = ""
    if hero:
        cfg = hero.get("config", {})
        hero_label = (
            cfg.get("label")
            or cfg.get("text")
            or cfg.get("title")
            or cfg.get("children")
            or hero.get("primitive", "?")
        )

    # Supporting objects (everything active that isn't the hero)
    supporting = [
        l.get("config", {}).get("label")
        or l.get("config", {}).get("text")
        or l.get("primitive")
        for l, _ in layer_areas if l is not hero
    ]

    # Visual priority ordering by area
    visual_priority = [
        (l.get("config", {}).get("label") or l.get("primitive"), f"{a*100:.1f}%")
        for l, a in layer_areas
    ]

    # Frame occupancy
    total_occupancy = sum(a for _, a in layer_areas)

    # Entry action for hero
    entry_action = _layer_entry_style(hero) if hero and hero in [l for l in entering_layers] else "carry"

    # Primary action from beat text
    primary_action = beat.get("action", "")[:80]

    # Result state — what's on screen at beat end
    result_labels = [
        l.get("config", {}).get("label")
        or l.get("config", {}).get("text")
        or l.get("primitive")
        for l, _ in layer_areas
    ]

    # Determine what carries to next beat
    carry_objects = [
        l.get("config", {}).get("label") or l.get("primitive")
        for l, _ in layer_areas
        if l.get("activeBeat", 0) <= beat_idx  # persists
    ]

    # Environment treatment
    env_layers = [
        l for l in active_layers
        if l.get("primitive") in ("CameraTransform", "SpatialZone", "DualLaneLayout")
    ]
    env_treatment = ", ".join(
        l.get("primitive") + (f"({l.get('config', {}).get('operation', '')})" if l.get("primitive") == "CameraTransform" else "")
        for l in env_layers
    ) or "dark void (default)"

    # ── Apply composition rules ──────────────────────────────────────────
    violations: list[dict[str, str]] = []

    # R01: hero_exists
    if not hero and component == "ComposedScene":
        violations.append({"rule": "R01", "issue": "No hero_object identified"})

    # R02: hero_dominance — primitive-aware thresholds
    hero_width_px = _estimate_layer_width(hero) if hero else 0
    hero_height_px = _estimate_layer_height(hero) if hero else 0
    hero_width_frac = hero_width_px / FRAME_W if hero else 0
    hero_height_frac = hero_height_px / FRAME_H if hero else 0
    if hero:
        r02_pass, r02_reason = _check_hero_dominance(hero, hero_area, camera, action_text)
        if not r02_pass:
            violations.append({"rule": "R02", "issue": r02_reason})

    # R03: element_count
    visible_count = len([l for l, a in layer_areas if a > 0.005])
    if visible_count > 5:
        violations.append({
            "rule": "R03",
            "issue": f"{visible_count} visible elements (max 5)",
        })

    # R04: z_hierarchy — strict semantic hierarchy
    # Hero must be above all supporting semantic objects.
    # Only StampOverlay allowed above hero when stamp IS the beat's primary action.
    stamp_is_primary = "stamp" in extract_actions_from_beat(beat)
    if hero and active_layers:
        hero_z = hero.get("zIndex", 0)
        semantic_above: list[tuple[int, str, str]] = []
        for l in active_layers:
            if l is hero:
                continue
            lp = l.get("primitive", "")
            if lp in ("CameraTransform", "ColorTransform"):
                continue
            lz = l.get("zIndex", 0)
            if lz <= hero_z:
                continue
            l_label = l.get("config", {}).get("label", l.get("config", {}).get("text", lp))
            if lp == "StampOverlay" and stamp_is_primary:
                continue
            semantic_above.append((lz, l_label, lp))
        if semantic_above and hero.get("primitive") != "StampOverlay":
            worst = max(semantic_above, key=lambda x: x[0])
            violations.append({
                "rule": "R04",
                "issue": f"Hero z={hero_z} below '{worst[1]}' ({worst[2]}) z={worst[0]}",
            })

    # R05: camera_matches_intent
    required_actions = extract_actions_from_beat(beat)
    expected_cameras = set()
    for act in required_actions:
        for cam, intents in CAMERA_INTENT_MAP.items():
            if act in intents:
                expected_cameras.add(cam)
    if camera not in expected_cameras and expected_cameras:
        violations.append({
            "rule": "R05",
            "issue": f"Camera '{camera}' doesn't match actions {sorted(required_actions)} — expected one of {sorted(expected_cameras)}",
        })

    # R06: entry_visible
    if entry_action not in ANIMATED_ENTRIES and entry_action != "carry":
        violations.append({
            "rule": "R06",
            "issue": f"Hero entry '{entry_action}' is not animated",
        })

    # R07: state_change
    if prev_beat_result and set(result_labels) == set(prev_beat_result.get("result_labels", [])):
        if not entering_layers:
            violations.append({
                "rule": "R07",
                "issue": "No visible state change from previous beat",
            })

    # R08: continuity — within scene AND cross-scene for declared continuity objects
    if prev_beat_result:
        prev_sid = prev_beat_result.get("scene_id", -1)
        prev_carry = set(prev_beat_result.get("carry_objects", []))
        current_active = set(result_labels)
        if prev_sid == sid:
            if prev_carry and not prev_carry.intersection(current_active):
                violations.append({
                    "rule": "R08",
                    "issue": f"Previous carry {sorted(prev_carry)} not present in current beat",
                })
        else:
            cont_obj = EP03_CONTINUITY.get("object", "")
            handoffs = EP03_CONTINUITY.get("handoffs", [])
            if (prev_sid, sid) in handoffs and cont_obj:
                cont_in_prev = any(cont_obj in c for c in prev_carry)
                cont_in_current = any(cont_obj in c for c in current_active)
                has_break = beat.get("continuity_break") == "intentional"
                if cont_in_prev and not cont_in_current and not has_break:
                    violations.append({
                        "rule": "R08",
                        "issue": f"Cross-scene continuity: {cont_obj} active in S{prev_sid:02d} end but not in S{sid:02d} B0",
                    })

    # R09: environment_subdued — structural env must be visually subordinate
    # unless beat explicitly makes the env the semantic subject
    beat_subject_is_env = any(
        kw in action_text for kw in ("zone", "layout", "lane", "establish", "grid")
    )
    for el in env_layers:
        if el is hero:
            continue
        ep = el.get("primitive", "")
        if ep == "CameraTransform":
            continue
        env_area = _estimate_layer_area(el)
        if env_area > hero_area and hero_area > 0 and not beat_subject_is_env:
            violations.append({
                "rule": "R09",
                "issue": (
                    f"Structural env {ep} area ({env_area*100:.1f}%) "
                    f"exceeds hero ({hero_area*100:.1f}%) — "
                    f"env must be subordinate unless beat makes it the subject"
                ),
            })

    # R10: checked at scene level, not beat level

    hero_prim = hero.get("primitive", "") if hero else ""

    return {
        "scene_id": sid,
        "beat_index": beat_idx,
        "hero_object": hero_label,
        "hero_primitive": hero_prim,
        "hero_area_pct": round(hero_area * 100, 1),
        "hero_width_px": round(hero_width_px),
        "hero_height_px": round(hero_height_px),
        "hero_width_pct": round(hero_width_frac * 100, 1),
        "hero_height_pct": round(hero_height_frac * 100, 1),
        "visual_priority": visual_priority,
        "frame_occupancy_pct": round(total_occupancy * 100, 1),
        "visible_elements": visible_count,
        "supporting_objects": supporting,
        "camera_intent": camera,
        "entry_action": entry_action,
        "primary_action": primary_action,
        "result_labels": result_labels,
        "carry_objects": carry_objects,
        "exit_or_carryover": ", ".join(carry_objects[:3]) if carry_objects else "none",
        "environment_treatment": env_treatment,
        "violations": violations,
        "pass": len(violations) == 0,
    }


def check_orphan_layers(scene: dict[str, Any]) -> list[dict[str, str]]:
    """R10: Check for layers that are never active in any beat."""
    data = scene.get("data", {})
    layers = data.get("layers", []) if isinstance(data, dict) else []
    beats = scene.get("beats", [])
    num_beats = len(beats)
    violations: list[dict[str, str]] = []

    for li, layer in enumerate(layers):
        ab = layer.get("activeBeat", 0)
        if ab >= num_beats:
            cfg = layer.get("config", {})
            label = cfg.get("label") or cfg.get("text") or layer.get("primitive")
            violations.append({
                "rule": "R10",
                "issue": f"Layer '{label}' (activeBeat={ab}) never active — scene has {num_beats} beats",
            })
    return violations


def analyze_composition_quality(
    storyboard: list[dict[str, Any]],
    scene_range: tuple[int, int] = (3, 8),
) -> dict[str, Any]:
    """Run full composition quality analysis on specified scene range."""
    results: list[dict[str, Any]] = []
    all_violations: list[dict[str, Any]] = []
    prev_beat_result: dict[str, Any] | None = None

    for scene in storyboard:
        sid = scene.get("scene_id", 0)
        if sid < scene_range[0] or sid > scene_range[1]:
            continue

        beats = scene.get("beats", [])
        orphan_violations = check_orphan_layers(scene)

        for bi, beat in enumerate(beats):
            analysis = analyze_beat_composition(scene, bi, beat, prev_beat_result)
            results.append(analysis)
            all_violations.extend(
                {**v, "scene_id": sid, "beat_index": bi} for v in analysis["violations"]
            )
            prev_beat_result = analysis

        all_violations.extend(
            {**v, "scene_id": sid, "beat_index": -1} for v in orphan_violations
        )

    total_beats = len(results)
    passing_beats = sum(1 for r in results if r["pass"])

    return {
        "total_beats_analyzed": total_beats,
        "passing_beats": passing_beats,
        "quality_score": f"{passing_beats}/{total_beats}",
        "all_pass": passing_beats == total_beats,
        "violations": all_violations,
        "beats": results,
    }


def format_choreography_table(analysis: dict[str, Any]) -> str:
    """Format composition analysis as a readable choreography table."""
    lines: list[str] = []

    lines.append("=" * 120)
    lines.append("COMPOSITION / CHOREOGRAPHY TABLE")
    lines.append("=" * 120)
    lines.append("")

    for beat in analysis["beats"]:
        sid = beat["scene_id"]
        bi = beat["beat_index"]
        status = "PASS" if beat["pass"] else "FAIL"

        lines.append(f"S{sid:02d} B{bi}  [{status}]")
        lines.append(f"  hero_object:          {beat['hero_object']} ({beat['hero_area_pct']}% area)")
        lines.append(f"  visible_elements:     {beat['visible_elements']}")
        lines.append(f"  frame_occupancy:      {beat['frame_occupancy_pct']}%")
        lines.append(f"  supporting_objects:    {', '.join(beat['supporting_objects'][:4]) or 'none'}")
        lines.append(f"  camera_intent:        {beat['camera_intent']}")
        lines.append(f"  entry_action:         {beat['entry_action']}")
        lines.append(f"  primary_action:       {beat['primary_action']}")
        lines.append(f"  exit_or_carryover:    {beat['exit_or_carryover']}")
        lines.append(f"  environment:          {beat['environment_treatment']}")

        if beat["violations"]:
            for v in beat["violations"]:
                lines.append(f"  !! {v['rule']}: {v['issue']}")
        lines.append("")

    lines.append("-" * 120)
    lines.append(f"Quality: {analysis['quality_score']} beats pass  |  "
                 f"Violations: {len(analysis['violations'])}")
    lines.append("")

    if analysis["violations"]:
        lines.append("VIOLATION SUMMARY:")
        rule_counts: dict[str, int] = {}
        for v in analysis["violations"]:
            rule_counts[v["rule"]] = rule_counts.get(v["rule"], 0) + 1
        for rule_id, count in sorted(rule_counts.items()):
            rule_name = next(
                (r["name"] for r in COMPOSITION_RULES if r["id"] == rule_id), "?"
            )
            lines.append(f"  {rule_id} ({rule_name}): {count}x")

    lines.append("=" * 120)
    return "\n".join(lines)


def run(episode: int, week: int, input_data: dict[str, Any]) -> dict[str, Any]:
    """Standard agent signature — validate and recompose storyboard."""
    storyboard_path = Path(input_data.get("storyboard_path", ""))
    if not storyboard_path.exists():
        raise FileNotFoundError(f"Storyboard not found: {storyboard_path}")

    with open(storyboard_path, "r", encoding="utf-8") as f:
        sb_data = json.load(f)

    storyboard = sb_data.get("storyboard", [])

    logger.info(f"EP{episode:02d} — Scene Composer validating {len(storyboard)} scenes")

    pre_validation = validate_beat_coverage(storyboard)
    logger.info(
        f"EP{episode:02d} — Pre-recomposition coverage: "
        f"{pre_validation['coverage']}"
    )

    recomposed = recompose_storyboard(storyboard)

    post_validation = validate_beat_coverage(recomposed)
    logger.info(
        f"EP{episode:02d} — Post-recomposition coverage: "
        f"{post_validation['coverage']}"
    )

    if not post_validation["all_covered"]:
        uncovered = [
            b for b in post_validation["beats"] if not b["covered"]
        ]
        for ub in uncovered:
            logger.error(
                f"EP{episode:02d} — UNCOVERED beat S{ub['scene_id']:02d}B{ub['beat_index']}: "
                f"needs {ub['missing_actions']} — {ub['component']} lacks these"
            )
        raise RuntimeError(
            f"EP{episode:02d} — Scene Composer FAIL: "
            f"{post_validation['coverage']} beats covered. "
            f"Cannot render with incomplete coverage."
        )

    sb_data["storyboard"] = recomposed
    output_path = storyboard_path.parent / f"ep{episode:02d}_storyboard_composed.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sb_data, f, indent=2, ensure_ascii=False)

    beat_table: list[str] = []
    beat_table.append(
        f"{'Scene':>6} {'Beat':>5} {'Component':<20} {'Required':<30} {'Status':<8}"
    )
    beat_table.append("-" * 75)
    for b in post_validation["beats"]:
        status = "OK" if b["covered"] else "FAIL"
        beat_table.append(
            f"S{b['scene_id']:02d}    "
            f"B{b['beat_index']:<4} "
            f"{b['component']:<20} "
            f"{', '.join(b['required_actions']):<30} "
            f"{status:<8}"
        )
    table_str = "\n".join(beat_table)
    logger.info(f"EP{episode:02d} — Beat Realization Table:\n{table_str}")

    # ── Composition Quality Analysis ─────────────────────────────────────
    composition = analyze_composition_quality(recomposed)
    choreo_table = format_choreography_table(composition)
    logger.info(f"EP{episode:02d} — Composition Quality:\n{choreo_table}")

    choreo_path = storyboard_path.parent / f"ep{episode:02d}_choreography.txt"
    choreo_path.write_text(choreo_table, encoding="utf-8")

    composition_json_path = storyboard_path.parent / f"ep{episode:02d}_composition.json"
    with open(composition_json_path, "w", encoding="utf-8") as f:
        json.dump(composition, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "output_path": str(output_path),
        "pre_coverage": pre_validation["coverage"],
        "post_coverage": post_validation["coverage"],
        "beat_table": table_str,
        "all_covered": post_validation["all_covered"],
        "composition_quality": composition["quality_score"],
        "composition_all_pass": composition["all_pass"],
        "composition_violations": len(composition["violations"]),
        "choreography_path": str(choreo_path),
    }
