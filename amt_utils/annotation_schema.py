page_schema = {
    "type": "object",
    "$schema": "http://json-schema.org/draft-04/schema",
    "additionalProperties": False,
    "properties": {
        "text": {
            "type": "object",
            "additionalProperties": False,
            "patternProperties": {
                "^T[0-9]+$": {
                    "type": "object",
                    "required": ["rectangle", "category", "box_id", "source", "score", "contents"],
                    "additionalProperties": False,
                    "properties": {
                        "box_id": {
                            "type": "string"
                        },
                        "category": {
                                "enum": ["header/topic", "definition", "discussion", "question", "answer",
                                         "figure_label", "unlabeled"]
                            },
                        "contents": {
                            "type": "string"
                        },
                        "score": {
                        },
                        "rectangle": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "items": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 2,
                                "items": {
                                    "type": "integer",
                                },
                            },
                        },
                        "source": {
                            "type": "object",
                            "items": {
                                "$schema": "http://json-schema.org/draft-04/schema#",
                                "title": "C Object",

                                "type": "object",
                                "required": ["book_source", "page_n"],

                                "properties": {
                                    "book_source": {
                                        "type": "string"
                                    },
                                    "page_n": {
                                        "type": "int"
                                    }
                                },
                                "additionalProperties": False
                            }
                        }
                    }
                }
            }
        },
        "figure": {
            "type": "object",
        },
        "relationship": {
            "type": "object",
        }
    },
    "required properties": ["text", "figure", "relationship"]
}

