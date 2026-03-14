"""Schema example tools for each top-level document type."""

import json

from .mcp_instance import mcp


@mcp.tool()
def get_acquisition_example() -> dict:
    """
    Example of the acquisition schema.
    ALL data collection uses 'acquisition' regardless of modality
    (imaging or physiology). Contains data_streams, stimulus_epochs,
    subject_details, manipulations, calibrations, and maintenance.
    Access fields like this - acquisition.<field_name>
    """
    sample_acquisition = json.dumps(
        {
            "acquisition": {
                "subject_id": "730945",
                "specimen_id": None,
                "instrument_id": "447-2-B_20240827",
                "acquisition_start_time": "2024-09-03T15:49:53-07:00",
                "acquisition_end_time": "2024-09-03T17:04:59-07:00",
                "acquisition_type": "Behavior",
                "experimenters": ["Bowen Tan"],
                "protocol_id": ["dx.doi.org/10.17504/protocols.io.example"],
                "calibrations": [],
                "maintenance": [],
                "coordinate_system": None,
                "subject_details": {
                    "animal_weight_prior": None,
                    "animal_weight_post": "23.6",
                    "weight_unit": "gram",
                    "anaesthesia": None,
                    "mouse_platform_name": "mouse_tube_foraging",
                    "reward_consumed_total": "372.0",
                    "reward_consumed_unit": "microliter",
                },
                "data_streams": [
                    {
                        "stream_start_time": "2024-09-03T15:49:53-07:00",
                        "stream_end_time": "2024-09-03T17:04:59-07:00",
                        "modalities": [
                            {"name": "Behavior", "abbreviation": "behavior"}
                        ],
                        "active_devices": [
                            "Harp Behavior",
                            "Harp Sound",
                            "Lick Sensor Left",
                            "Lick Sensor Right",
                        ],
                        "configurations": [],
                        "connections": [],
                        "code": [
                            {
                                "name": "dynamic-foraging-task",
                                "version": "1.4.4",
                                "url": "https://github.com/AllenNeuralDynamics/dynamic-foraging-task.git",
                                "parameters": {},
                            }
                        ],
                        "notes": None,
                    }
                ],
                "stimulus_epochs": [
                    {
                        "stimulus_start_time": "2024-09-03T15:49:53-07:00",
                        "stimulus_end_time": "2024-09-03T17:04:59-07:00",
                        "stimulus_name": "auditory go cue",
                        "stimulus_modalities": ["Auditory"],
                        "code": [
                            {
                                "name": "dynamic-foraging-task",
                                "version": "1.4.4",
                                "url": "https://github.com/AllenNeuralDynamics/dynamic-foraging-task.git",
                                "parameters": {},
                            }
                        ],
                        "performance_metrics": {
                            "trials_total": 493,
                            "trials_finished": 434,
                            "trials_rewarded": 186,
                            "foraging_efficiency": 0.593,
                        },
                        "active_devices": [],
                        "configurations": [],
                        "notes": None,
                    }
                ],
                "manipulations": [],
                "notes": None,
            }
        }
    )
    return sample_acquisition


@mcp.tool()
def get_data_description_example():
    """
    Example of the data description schema.
    Contains modalities (plural), investigators as Person objects, and tags.
    Access fields like this - data_description.<field_name>
    """
    sample_data_description = json.dumps(
        {
            "data_description": {
                "license": "CC-BY-4.0",
                "subject_id": "662616",
                "creation_time": "2023-04-14T15:11:04-07:00",
                "name": "SmartSPIM_662616_2023-04-14_15-11-04",
                "institution": {
                    "name": "Allen Institute for Neural Dynamics",
                    "abbreviation": "AIND",
                    "registry": {
                        "name": "Research Organization Registry",
                        "abbreviation": "ROR",
                    },
                    "registry_identifier": "04szwah67",
                },
                "funding_source": [
                    {
                        "funder": {
                            "name": "National Institute of Neurological Disorders and Stroke",
                            "abbreviation": "NINDS",
                            "registry": {
                                "name": "Research Organization Registry",
                                "abbreviation": "ROR",
                            },
                            "registry_identifier": "01s5ya894",
                        },
                        "grant_number": "NIH1U19NS123714-01",
                        "fundee": "Jayaram Chandrashekar, Mathew Summers",
                    }
                ],
                "data_level": "raw",
                "group": "MSMA",
                "investigators": [
                    {
                        "name": "Mathew Summers",
                        "registry": None,
                        "registry_identifier": None,
                    },
                    {
                        "name": "Jayaram Chandrashekar",
                        "registry": None,
                        "registry_identifier": None,
                    },
                ],
                "project_name": "Thalamus in the middle",
                "restrictions": None,
                "modalities": [
                    {
                        "name": "Selective plane illumination microscopy",
                        "abbreviation": "SPIM",
                    }
                ],
                "tags": [],
                "source_data": None,
                "data_summary": None,
            },
        }
    )
    return sample_data_description


@mcp.tool()
def get_instrument_example():
    """
    Example of the instrument schema.
    All devices are in a single 'components' list.
    Contains 'connections', 'coordinate_system', 'modalities', 'modification_date'.
    Access fields like this - instrument.<field_name>
    """
    sample_instrument = json.dumps(
        {
            "instrument": {
                "instrument_id": "SmartSPIM1-2",
                "location": "615 Westlake",
                "modification_date": "2023-01-15",
                "temperature_control": None,
                "modalities": [
                    {
                        "name": "Selective plane illumination microscopy",
                        "abbreviation": "SPIM",
                    }
                ],
                "components": [
                    {
                        "device_type": "Objective",
                        "name": "TL4X-SAP",
                        "serial_number": "Unknown",
                        "manufacturer": {
                            "name": "Thorlabs",
                            "abbreviation": None,
                            "registry": {
                                "name": "Research Organization Registry",
                                "abbreviation": "ROR",
                            },
                            "registry_identifier": "04gsnvb07",
                        },
                        "model": "TL4X-SAP",
                        "notes": "Thorlabs TL4X-SAP with LifeCanvas dipping cap and correction optics",
                        "numerical_aperture": 0.2,
                        "magnification": 3.6,
                        "immersion": "multi",
                    },
                    {
                        "device_type": "Detector",
                        "name": "Camera",
                        "serial_number": "220302-SYS-060443",
                        "manufacturer": {
                            "name": "Hamamatsu",
                            "abbreviation": None,
                            "registry": None,
                            "registry_identifier": None,
                        },
                        "model": "C14440-20UP",
                        "notes": None,
                        "detector_type": "Camera",
                        "data_interface": "USB",
                        "cooling": "water",
                    },
                    {
                        "device_type": "Laser",
                        "name": "488nm Laser",
                        "serial_number": "VL08223M03",
                        "manufacturer": {
                            "name": "Vortran",
                            "abbreviation": None,
                            "registry": None,
                            "registry_identifier": None,
                        },
                        "model": "Stradus",
                        "notes": "All lasers controlled via Vortran VersaLase System",
                        "coupling": "Single-mode fiber",
                        "wavelength": 488,
                        "wavelength_unit": "nanometer",
                        "max_power": 150,
                        "power_unit": "milliwatt",
                    },
                    {
                        "device_type": "Filter",
                        "name": "469/35 Band Pass",
                        "serial_number": "Unknown-0",
                        "manufacturer": {
                            "name": "Semrock",
                            "abbreviation": None,
                            "registry": None,
                            "registry_identifier": None,
                        },
                        "model": "FF01-469/35-25",
                        "notes": None,
                        "filter_type": "Band pass",
                        "diameter": 25,
                        "diameter_unit": "millimeter",
                        "filter_wheel_index": 0,
                    },
                    {
                        "device_type": "Motorized stage",
                        "name": "Focus stage",
                        "serial_number": "Unknown-0",
                        "manufacturer": {
                            "name": "Applied Scientific Instrumentation",
                            "abbreviation": None,
                            "registry": None,
                            "registry_identifier": None,
                        },
                        "model": "LS-100",
                        "notes": "Focus stage",
                        "travel": 100,
                        "travel_unit": "millimeter",
                    },
                ],
                "connections": [],
                "coordinate_system": None,
                "notes": None,
            },
        }
    )
    return sample_instrument


@mcp.tool()
def get_procedures_example():
    """
    Example of the procedures schema.
    Access fields like this - procedures.<field_name>
    """
    sample_procedures = json.dumps(
        {
            "procedures": {
                "subject_id": "662616",
                "subject_procedures": [
                    {
                        "procedure_type": "Surgery",
                        "start_date": "2023-02-03",
                        "experimenter_full_name": "30509",
                        "iacuc_protocol": None,
                        "animal_weight_prior": None,
                        "animal_weight_post": None,
                        "weight_unit": "gram",
                        "anaesthesia": None,
                        "workstation_id": None,
                        "procedures": [
                            {
                                "procedure_type": "Perfusion",
                                "protocol_id": "dx.doi.org/10.17504/protocols.io.bg5vjy66",
                                "output_specimen_ids": ["662616"],
                            }
                        ],
                        "notes": None,
                    },
                    {
                        "procedure_type": "Surgery",
                        "start_date": "2023-01-05",
                        "experimenter_full_name": "NSB-5756",
                        "iacuc_protocol": "2109",
                        "animal_weight_prior": "16.6",
                        "animal_weight_post": "16.7",
                        "weight_unit": "gram",
                        "anaesthesia": {
                            "type": "isoflurane",
                            "duration": "120.0",
                            "duration_unit": "minute",
                            "level": "1.5",
                        },
                        "workstation_id": "SWS 1",
                        "procedures": [
                            {
                                "injection_materials": [
                                    {
                                        "material_type": "Virus",
                                        "name": "SL1-hSyn-Cre",
                                        "tars_identifiers": {
                                            "virus_tars_id": None,
                                            "plasmid_tars_alias": None,
                                            "prep_lot_number": "221118-11",
                                            "prep_date": None,
                                            "prep_type": None,
                                            "prep_protocol": None,
                                        },
                                        "addgene_id": None,
                                        "titer": {
                                            "$numberLong": "37500000000000"
                                        },
                                        "titer_unit": "gc/mL",
                                    }
                                ],
                                "recovery_time": "10.0",
                                "recovery_time_unit": "minute",
                                "injection_duration": None,
                                "injection_duration_unit": "minute",
                                "instrument_id": "NJ#2",
                                "protocol_id": "dx.doi.org/10.17504/protocols.io.bgpujvnw",
                                "injection_coordinate_ml": "0.35",
                                "injection_coordinate_ap": "2.2",
                                "injection_coordinate_depth": ["2.1"],
                                "injection_coordinate_unit": "millimeter",
                                "injection_coordinate_reference": "Bregma",
                                "bregma_to_lambda_distance": "4.362",
                                "bregma_to_lambda_unit": "millimeter",
                                "injection_angle": "0",
                                "injection_angle_unit": "degrees",
                                "targeted_structure": "mPFC",
                                "injection_hemisphere": "Right",
                                "procedure_type": "Nanoject injection",
                                "injection_volume": ["200"],
                                "injection_volume_unit": "nanoliter",
                            },
                            {
                                "injection_materials": [
                                    {
                                        "material_type": "Virus",
                                        "name": "AAV-Syn-DIO-TVA66T-dTomato-CVS N2cG",
                                        "tars_identifiers": {
                                            "virus_tars_id": None,
                                            "plasmid_tars_alias": None,
                                            "prep_lot_number": "220916-4",
                                            "prep_date": None,
                                            "prep_type": None,
                                            "prep_protocol": None,
                                        },
                                        "addgene_id": None,
                                        "titer": {
                                            "$numberLong": "18000000000000"
                                        },
                                        "titer_unit": "gc/mL",
                                    }
                                ],
                                "recovery_time": "10.0",
                                "recovery_time_unit": "minute",
                                "injection_duration": None,
                                "injection_duration_unit": "minute",
                                "instrument_id": "NJ#2",
                                "protocol_id": "dx.doi.org/10.17504/protocols.io.bgpujvnw",
                                "injection_coordinate_ml": "2.9",
                                "injection_coordinate_ap": "-0.6",
                                "injection_coordinate_depth": ["3.6"],
                                "injection_coordinate_unit": "millimeter",
                                "injection_coordinate_reference": "Bregma",
                                "bregma_to_lambda_distance": "4.362",
                                "bregma_to_lambda_unit": "millimeter",
                                "injection_angle": "30",
                                "injection_angle_unit": "degrees",
                                "targeted_structure": "VM",
                                "injection_hemisphere": "Right",
                                "procedure_type": "Nanoject injection",
                                "injection_volume": ["200"],
                                "injection_volume_unit": "nanoliter",
                            },
                        ],
                        "notes": None,
                    },
                ],
                "specimen_procedures": [
                    {
                        "procedure_type": "Fixation",
                        "procedure_name": "SHIELD OFF",
                        "specimen_id": "662616",
                        "start_date": "2023-02-10",
                        "end_date": "2023-02-12",
                        "experimenter_full_name": "DT",
                        "protocol_id": "none",
                        "reagents": [
                            {
                                "name": "SHIELD Epoxy",
                                "source": "LiveCanvas Technologies",
                                "rrid": None,
                                "lot_number": "unknown",
                                "expiration_date": None,
                            }
                        ],
                        "hcr_series": None,
                        "immunolabeling": None,
                        "notes": "None",
                    },
                ],
                "notes": None,
            },
        }
    )
    return sample_procedures


@mcp.tool()
def get_subject_example():
    """
    Example of the subject schema.
    Species, sex, genotype, breeding_info, and housing are nested inside
    'subject_details' (MouseSubject/HumanSubject/CalibrationObject).
    Access fields like this - subject.<field_name>
    """
    sample_subject = json.dumps(
        {
            "subject": {
                "subject_id": "662616",
                "subject_details": {
                    "species": {
                        "name": "Mus musculus",
                        "abbreviation": None,
                        "registry": {
                            "name": "National Center for Biotechnology Information",
                            "abbreviation": "NCBI",
                        },
                        "registry_identifier": "10090",
                    },
                    "strain": {
                        "name": "C57BL/6J",
                        "registry": None,
                        "registry_identifier": None,
                    },
                    "sex": "Male",
                    "date_of_birth": "2022-11-29",
                    "genotype": "Emx1-IRES-Cre/wt;Camk2a-tTA/wt;Ai93(TITL-GCaMP6f)/wt",
                    "source": {
                        "name": "Allen Institute",
                        "abbreviation": "AI",
                        "registry": None,
                        "registry_identifier": None,
                    },
                    "breeding_info": {
                        "breeding_group": "Emx1-IRES-Cre(ND)",
                        "maternal_id": "546543",
                        "maternal_genotype": "Emx1-IRES-Cre/wt; Camk2a-tTa/Camk2a-tTA",
                        "paternal_id": "232323",
                        "paternal_genotype": "Ai93(TITL-GCaMP6f)/wt",
                    },
                    "housing": {
                        "home_cage_enrichment": ["Running wheel"],
                        "cage_id": "123",
                    },
                },
                "notes": None,
            }
        }
    )
    return sample_subject


@mcp.tool()
def get_processing_example():
    """
    Example of the processing schema.
    Contains 'data_processes' and 'pipelines' lists.
    Access fields like this - processing.<field_name>
    """
    sample_processing = json.dumps(
        {
            "processing": {
                "data_processes": [
                    {
                        "process_type": "Image tile fusing",
                        "name": "Image tile fusing",
                        "stage": "Processing",
                        "code": {
                            "url": "https://github.com/abcd",
                            "version": "0.1",
                            "parameters": {"size": 7},
                        },
                        "experimenters": ["Dr. Dan"],
                        "start_date_time": "2022-11-22T08:43:00+00:00",
                        "end_date_time": "2022-11-22T08:43:00+00:00",
                        "output_path": "/path/to/outputs",
                        "notes": None,
                    }
                ],
                "pipelines": [
                    {
                        "name": "Imaging processing pipeline",
                        "url": "https://url/for/pipeline",
                        "version": "0.1.1",
                    }
                ],
                "dependency_graph": None,
                "notes": None,
            }
        }
    )

    return sample_processing


@mcp.tool()
def get_model_example() -> dict:
    """
    Example of the model schema.
    Describes a machine learning model including architecture, training, and evaluation.
    Access fields like this - model.<field_name>
    """
    sample_model = json.dumps(
        {
            "model": {
                "name": "Example segmentation model",
                "version": "1.0.0",
                "example_run_code": {
                    "url": "https://github.com/example/model",
                    "version": "1.0.0",
                    "parameters": {"input_shape": [256, 256, 3]},
                },
                "architecture": "UNet",
                "software_framework": {"name": "PyTorch", "version": "2.0"},
                "architecture_parameters": {"layers": 5, "filters": 64},
                "intended_use": "Cell segmentation in calcium imaging data",
                "limitations": "Trained only on mouse visual cortex data",
                "training": [],
                "evaluations": [],
                "notes": None,
            }
        }
    )
    return sample_model

