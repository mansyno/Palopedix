"""Tests for save file parser modules (extract_pals and extract_bases)."""

import pytest
from unittest.mock import patch
from uuid import UUID

from palengine.parser.extract_pals import extract_pals
from palengine.parser.extract_bases import extract_bases


class MockGvasFile:
    def __init__(self, properties):
        self.properties = properties


@pytest.fixture
def mock_world_save_data():
    player_uid_1 = UUID("11111111-1111-1111-1111-111111111111")
    player_uid_2 = UUID("22222222-2222-2222-2222-222222222222")

    otomo_container_1 = UUID("33333333-3333-3333-3333-333333333333")
    storage_container_1 = UUID("44444444-4444-4444-4444-444444444444")
    otomo_container_2 = UUID("55555555-5555-5555-5555-555555555555")
    storage_container_2 = UUID("66666666-6666-6666-6666-666666666666")

    base_camp_id_1 = UUID("77777777-7777-7777-7777-777777777777")
    base_camp_id_2 = UUID("88888888-8888-8888-8888-888888888888")
    worker_container_1 = UUID("99999999-9999-9999-9999-999999999999")
    worker_container_2 = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    # Character entries
    character_values = [
        # Player 1
        {
            "key": {
                "value": {
                    "PlayerUId": {"value": player_uid_1},
                    "InstanceId": {"value": UUID("00000000-0000-0000-0000-000000000001")}
                }
            },
            "value": {
                "RawData": {
                    "value": {
                        "object": {
                            "SaveParameter": {
                                "value": {
                                    "IsPlayer": {"value": True},
                                    "OtomoCharacterContainerId": {"value": {"value": otomo_container_1}},
                                    "PalStorageContainerId": {"value": {"value": storage_container_1}}
                                }
                            }
                        }
                    }
                }
            }
        },
        # Player 2
        {
            "key": {
                "value": {
                    "PlayerUId": {"value": player_uid_2},
                    "InstanceId": {"value": UUID("00000000-0000-0000-0000-000000000002")}
                }
            },
            "value": {
                "RawData": {
                    "value": {
                        "object": {
                            "SaveParameter": {
                                "value": {
                                    "IsPlayer": {"value": True},
                                    "OtomoCharacterContainerId": {"value": {"value": otomo_container_2}},
                                    "PalStorageContainerId": {"value": {"value": storage_container_2}}
                                }
                            }
                        }
                    }
                }
            }
        },
        # Pal 1: in Player 1's active party
        {
            "key": {
                "value": {
                    "PlayerUId": {"value": player_uid_1},
                    "InstanceId": {"value": UUID("00000000-0000-0000-0000-000000000003")}
                }
            },
            "value": {
                "RawData": {
                    "value": {
                        "object": {
                            "SaveParameter": {
                                "value": {
                                    "IsPlayer": {"value": False},
                                    "CharacterID": {"value": "SheepBall"},
                                    "Level": {"value": 15},
                                    "Gender": {"value": {"value": "EPalGenderType::Male"}},
                                    "Talent_HP": {"value": 50},
                                    "Talent_Melee": {"value": 60},
                                    "Talent_Shot": {"value": 70},
                                    "Talent_Defense": {"value": 80},
                                    "PassiveSkillList": {"value": {"values": ["Serious", "Artisan"]}},
                                    "Rank": {"value": 2},
                                    "SlotID": {
                                        "value": {
                                            "ContainerId": {"value": {"value": otomo_container_1}},
                                            "SlotIndex": {"value": 0}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        # Pal 2: in Player 1's Palbox
        {
            "key": {
                "value": {
                    "PlayerUId": {"value": player_uid_1},
                    "InstanceId": {"value": UUID("00000000-0000-0000-0000-000000000004")}
                }
            },
            "value": {
                "RawData": {
                    "value": {
                        "object": {
                            "SaveParameter": {
                                "value": {
                                    "IsPlayer": {"value": False},
                                    "CharacterID": {"value": "Grizzbolt"},
                                    "Level": {"value": 45},
                                    "Gender": {"value": {"value": "EPalGenderType::Female"}},
                                    "PassiveSkillList": {"value": {"values": ["Legend"]}},
                                    "Rank": {"value": 4},
                                    "SlotID": {
                                        "value": {
                                            "ContainerId": {"value": {"value": storage_container_1}},
                                            "SlotIndex": {"value": 12}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        # Pal 3: working at Base 1
        {
            "key": {
                "value": {
                    "PlayerUId": {"value": player_uid_1},
                    "InstanceId": {"value": UUID("00000000-0000-0000-0000-000000000005")}
                }
            },
            "value": {
                "RawData": {
                    "value": {
                        "object": {
                            "SaveParameter": {
                                "value": {
                                    "IsPlayer": {"value": False},
                                    "CharacterID": {"value": "Anubis"},
                                    "Level": {"value": 50},
                                    "Gender": {"value": {"value": "EPalGenderType::Male"}},
                                    "SlotID": {
                                        "value": {
                                            "ContainerId": {"value": {"value": worker_container_1}},
                                            "SlotIndex": {"value": 2}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    ]

    # Base Camp entries
    base_camp_values = [
        {
            "value": {
                "RawData": {
                    "value": {
                        "id": base_camp_id_1,
                        "name": "Main Base"
                    }
                },
                "WorkerDirector": {
                    "value": {
                        "RawData": {
                            "value": {
                                "container_id": worker_container_1
                            }
                        }
                    }
                }
            }
        },
        {
            "value": {
                "RawData": {
                    "value": {
                        "id": base_camp_id_2,
                        "name": "Ore Base"
                    }
                },
                "WorkerDirector": {
                    "value": {
                        "RawData": {
                            "value": {
                                "container_id": worker_container_2
                            }
                        }
                    }
                }
            }
        }
    ]

    # Map Object entries (for structure counts)
    map_object_values = [
        {
            "ObjectId": {"value": "straw_pal_bed"},
            "Model": {
                "value": {
                    "RawData": {
                        "value": {
                            "base_camp_id_belong_to": base_camp_id_1
                        }
                    }
                }
            }
        },
        {
            "ObjectId": {"value": "straw_pal_bed"},
            "Model": {
                "value": {
                    "RawData": {
                        "value": {
                            "base_camp_id_belong_to": base_camp_id_1
                        }
                    }
                }
            }
        },
        {
            "ObjectId": {"value": "electric_furnace"},
            "Model": {
                "value": {
                    "RawData": {
                        "value": {
                            "base_camp_id_belong_to": base_camp_id_1
                        }
                    }
                }
            }
        },
        {
            "ObjectId": {"value": "breeding_farm"},
            "Model": {
                "value": {
                    "RawData": {
                        "value": {
                            "base_camp_id_belong_to": base_camp_id_2
                        }
                    }
                }
            }
        },
        {
            "ObjectId": {"value": "crusher"},
            "Model": {
                "value": {
                    "RawData": {
                        "value": {
                            "base_camp_id_belong_to": UUID("00000000-0000-0000-0000-000000000000") # belong to no base
                        }
                    }
                }
            }
        }
    ]

    properties = {
        "worldSaveData": {
            "value": {
                "CharacterSaveParameterMap": {"value": character_values},
                "BaseCampSaveData": {"value": base_camp_values},
                "MapObjectSaveData": {"value": {"values": map_object_values}}
            }
        }
    }
    return properties


def test_extract_pals(mock_world_save_data):
    mock_gvas = MockGvasFile(mock_world_save_data)
    with patch("palengine.parser.extract_pals.load_gvas_from_sav", return_value=mock_gvas):
        pals = extract_pals("dummy_path.sav")
        assert len(pals) == 3

        # Pal 1 assertions (Party)
        pal1 = [p for p in pals if p["species"] == "SheepBall"][0]
        assert pal1["level"] == 15
        assert pal1["gender"] == "Male"
        assert pal1["ivs"]["hp"] == 50
        assert pal1["ivs"]["melee"] == 60
        assert pal1["passives"] == ["Serious", "Artisan"]
        assert pal1["rank"] == 2
        assert pal1["location"] == "party"
        assert pal1["location_details"]["player_uid"] == "11111111-1111-1111-1111-111111111111"

        # Pal 2 assertions (Palbox)
        pal2 = [p for p in pals if p["species"] == "Grizzbolt"][0]
        assert pal2["level"] == 45
        assert pal2["gender"] == "Female"
        assert pal2["passives"] == ["Legend"]
        assert pal2["rank"] == 4
        assert pal2["location"] == "palbox"
        assert pal2["location_details"]["player_uid"] == "11111111-1111-1111-1111-111111111111"

        # Pal 3 assertions (Base Camp)
        pal3 = [p for p in pals if p["species"] == "Anubis"][0]
        assert pal3["level"] == 50
        assert pal3["location"] == "base"
        assert pal3["location_details"]["base_camp_name"] == "Main Base"


def test_extract_bases(mock_world_save_data):
    mock_gvas = MockGvasFile(mock_world_save_data)
    with patch("palengine.parser.extract_bases.load_gvas_from_sav", return_value=mock_gvas):
        bases = extract_bases("dummy_path.sav")
        assert len(bases) == 2

        # Base 1 assertions
        base1_id = "77777777-7777-7777-7777-777777777777"
        assert base1_id in bases
        assert bases[base1_id]["name"] == "Main Base"
        assert bases[base1_id]["structures"] == {
            "straw_pal_bed": 2,
            "electric_furnace": 1
        }

        # Base 2 assertions
        base2_id = "88888888-8888-8888-8888-888888888888"
        assert base2_id in bases
        assert bases[base2_id]["name"] == "Ore Base"
        assert bases[base2_id]["structures"] == {
            "breeding_farm": 1
        }
