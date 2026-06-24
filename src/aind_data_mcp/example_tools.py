"""Schema example tools for each top-level document type."""

from .mcp_instance import mcp


@mcp.tool()
def get_acquisition_example() -> dict:
    """
    Example of the acquisition schema (V2).
    ALL data collection uses 'acquisition' regardless of modality
    (imaging or physiology). Contains data_streams, stimulus_epochs,
    calibrations, and maintenance.
    Access fields like this - acquisition.<field_name>
    """
    sample_acquisition = {
        "object_type": "Acquisition",
        "schema_version": "2.5.1",
        "subject_id": "664484",
        "instrument_id": "EPHYS1",
        "acquisition_start_time": "2023-04-25T02:35:00-07:00",
        "acquisition_end_time": "2023-04-25T03:16:00-07:00",
        "acquisition_type": "Receptive field mapping",
        "experimenters": ["John Smith"],
        "ethics_review_id": ["2109"],
        "calibrations": [],
        "maintenance": [],
        "coordinate_system": {
            "object_type": "Coordinate system",
            "name": "BREGMA_ARID",
            "origin": "Bregma",
            "axes": [
                {"object_type": "Axis", "name": "AP", "direction": "Posterior_to_anterior"},
                {"object_type": "Axis", "name": "ML", "direction": "Left_to_right"},
                {"object_type": "Axis", "name": "SI", "direction": "Superior_to_inferior"},
                {"object_type": "Axis", "name": "Depth", "direction": "Up_to_down"},
            ],
            "axis_unit": "millimeter",
        },
        "data_streams": [
            {
                "object_type": "Data stream",
                "stream_start_time": "2023-04-25T02:45:00-07:00",
                "stream_end_time": "2023-04-25T03:16:00-07:00",
                "modalities": [{"name": "Extracellular electrophysiology", "abbreviation": "ecephys"}],
                "active_devices": ["Basestation Slot 3", "Ephys_assemblyA"],
                "configurations": [],
                "code": None,
                "notes": None,
            }
        ],
        "stimulus_epochs": [
            {
                "object_type": "Stimulus epoch",
                "stimulus_start_time": "2023-04-25T02:45:00-07:00",
                "stimulus_end_time": "2023-04-25T03:16:00-07:00",
                "stimulus_name": "visual",
                "stimulus_modalities": ["Visual"],
                "code": {
                    "object_type": "Code",
                    "url": "https://github.com/AllenNeuralDynamics/visual-stimulus-task",
                    "version": "1.0.0",
                    "parameters": {},
                },
                "performance_metrics": None,
                "active_devices": [],
                "configurations": [],
                "notes": None,
            }
        ],
        "notes": None,
    }
    return sample_acquisition


@mcp.tool()
def get_data_description_example():
    """
    Example of the data description schema (V2).
    Contains modalities (plural), investigators as Person objects with ORCID, and tags.
    Access fields like this - data_description.<field_name>
    """
    sample_data_description = {
        "object_type": "Data description",
        "schema_version": "2.4.0",
        "license": "CC-BY-4.0",
        "subject_id": "123456",
        "creation_time": "2022-02-21T16:30:01Z",
        "name": "123456_2022-02-21_16-30-01",
        "institution": {
            "name": "Allen Institute for Neural Dynamics",
            "abbreviation": "AIND",
            "registry": "Research Organization Registry (ROR)",
            "registry_identifier": "04szwah67",
        },
        "funding_source": [
            {
                "object_type": "Funding",
                "funder": {
                    "name": "Allen Institute",
                    "abbreviation": "AI",
                    "registry": "Research Organization Registry (ROR)",
                    "registry_identifier": "03cpe7c52",
                },
                "grant_number": None,
                "fundee": None,
            }
        ],
        "data_level": "raw",
        "group": None,
        "investigators": [
            {
                "object_type": "Person",
                "name": "Daniel Birman",
                "registry": "Open Researcher and Contributor ID (ORCID)",
                "registry_identifier": "0000-0003-3748-6289",
            }
        ],
        "project_name": "Example project",
        "restrictions": None,
        "modalities": [
            {"name": "Extracellular electrophysiology", "abbreviation": "ecephys"},
            {"name": "Behavior videos", "abbreviation": "behavior-videos"},
        ],
        "tags": ["Pilot data"],
        "source_data": None,
        "data_summary": None,
    }
    return sample_data_description


@mcp.tool()
def get_instrument_example():
    """
    Example of the instrument schema (V2).
    All devices are in a 'components' list. Contains 'connections',
    'coordinate_system', 'modalities', 'calibrations', 'modification_date'.
    Access fields like this - instrument.<field_name>
    """
    sample_instrument = {
        "object_type": "Instrument",
        "schema_version": "2.2.5",
        "instrument_id": "EPHYS1",
        "location": "323",
        "modification_date": "2023-10-03",
        "modalities": [{"name": "Extracellular electrophysiology", "abbreviation": "ecephys"}],
        "calibrations": [
            {
                "object_type": "Calibration",
                "device_name": "Red Laser",
                "calibration_date": "2023-10-02T10:22:13Z",
                "description": "Laser power calibration",
                "input": [10.0, 20.0, 40.0],
                "input_unit": "percent",
                "output": [1.0, 3.0, 6.0],
                "output_unit": "milliwatt",
            }
        ],
        "coordinate_system": {
            "object_type": "Coordinate system",
            "name": "BREGMA_ARI",
            "origin": "Bregma",
            "axes": [
                {"object_type": "Axis", "name": "AP", "direction": "Posterior_to_anterior"},
                {"object_type": "Axis", "name": "ML", "direction": "Left_to_right"},
                {"object_type": "Axis", "name": "SI", "direction": "Superior_to_inferior"},
            ],
            "axis_unit": "millimeter",
        },
        "temperature_control": None,
        "connections": [
            {
                "object_type": "Connection",
                "source_device": "Harp Behavior",
                "source_port": "DO0",
                "target_device": "Face Camera",
                "target_port": None,
                "send_and_receive": False,
            }
        ],
        "components": [
            {
                "object_type": "Ephys assembly",
                "name": "Ephys_assemblyA",
                "manipulator": {
                    "object_type": "Manipulator",
                    "name": "Manipulator 1",
                    "serial_number": "SN2938",
                    "manufacturer": {"name": "New Scale Technologies"},
                    "model": None,
                },
                "probes": [
                    {
                        "object_type": "Ephys probe",
                        "name": "Probe A",
                        "serial_number": "9291019",
                        "probe_model": "Neuropixels 1.0",
                    }
                ],
            },
            {
                "object_type": "Camera",
                "name": "Face Camera",
                "serial_number": "12345",
                "manufacturer": {"name": "FLIR"},
                "model": "Blackfly S BFS-U3-04S2M-CS",
                "data_interface": "USB",
                "frame_rate": 30.0,
                "frame_rate_unit": "hertz",
            },
        ],
        "notes": None,
    }
    return sample_instrument


@mcp.tool()
def get_procedures_example():
    """
    Example of the procedures schema (V2).
    subject_procedures is a list of Surgery objects, each with a procedures list
    that can contain BrainInjection, Craniotomy, ProbeImplant, Perfusion, etc.
    Access fields like this - procedures.<field_name>
    """
    sample_procedures = {
        "object_type": "Procedures",
        "schema_version": "2.2.1",
        "subject_id": "625100",
        "subject_procedures": [
            {
                "object_type": "Surgery",
                "protocol_id": "doi",
                "start_date": "2022-07-12",
                "experimenters": ["Scientist Smith"],
                "ethics_review_id": "2109",
                "animal_weight_prior": 22.6,
                "animal_weight_post": 22.3,
                "weight_unit": "gram",
                "anaesthesia": {
                    "object_type": "Anaesthetic",
                    "anaesthetic_type": "Isoflurane",
                    "duration": 1.0,
                    "duration_unit": "minute",
                    "level": 1.5,
                },
                "workstation_id": "SWS 3",
                "procedures": [
                    {
                        "object_type": "Brain injection",
                        "protocol_id": "5678",
                        "injection_materials": [
                            {
                                "object_type": "Viral material",
                                "name": "AAV2-Flex-ChrimsonR",
                                "tars_identifiers": {
                                    "virus_tars_id": "AiV222",
                                    "prep_lot_number": "VT222",
                                },
                                "titer": 2300000000,
                                "titer_unit": "gc/mL",
                            }
                        ],
                        "targeted_structure": {
                            "atlas": "CCFv3",
                            "name": "Primary visual area",
                            "acronym": "VISp",
                            "id": "385",
                        },
                        "dynamics": [
                            {
                                "object_type": "Injection dynamics",
                                "profile": "Bolus",
                                "volume": 200.0,
                                "volume_unit": "nanoliter",
                            }
                        ],
                    },
                    {
                        "object_type": "Craniotomy",
                        "protocol_id": "1234",
                        "craniotomy_type": "Circle",
                        "size": 1.0,
                        "size_unit": "millimeter",
                    },
                ],
                "notes": None,
            },
            {
                "object_type": "Surgery",
                "protocol_id": "doi",
                "start_date": "2022-09-23",
                "experimenters": ["Scientist Smith"],
                "ethics_review_id": "2109",
                "procedures": [
                    {
                        "object_type": "Perfusion",
                        "protocol_id": "doi_of_protocol",
                        "output_specimen_ids": ["1", "2"],
                    }
                ],
                "notes": None,
            },
        ],
        "specimen_procedures": [],
        "notes": None,
    }
    return sample_procedures


@mcp.tool()
def get_subject_example():
    """
    Example of the subject schema (V2).
    Species, sex, genotype, breeding_info, and housing are nested inside
    'subject_details' (object_type: "Mouse subject").
    Access fields like this - subject.<field_name>
    """
    sample_subject = {
        "object_type": "Subject",
        "schema_version": "2.3.1",
        "subject_id": "123456",
        "subject_details": {
            "object_type": "Mouse subject",
            "sex": "Male",
            "date_of_birth": "2022-11-22",
            "strain": {
                "name": "C57BL/6J",
                "species": "Mus musculus",
                "registry": "Mouse Genome Informatics (MGI)",
                "registry_identifier": "MGI:3028467",
            },
            "species": {
                "name": "Mus musculus",
                "common_name": "House mouse",
                "registry": "National Center for Biotechnology Information (NCBI)",
                "registry_identifier": "NCBI:txid10090",
            },
            "alleles": [],
            "genotype": "Emx1-IRES-Cre/wt;Camk2a-tTA/wt;Ai93(TITL-GCaMP6f)/wt",
            "breeding_info": {
                "object_type": "Breeding info",
                "breeding_group": None,
                "maternal_id": "546543",
                "maternal_genotype": "Emx1-IRES-Cre/wt; Camk2a-tTa/Camk2a-tTA",
                "paternal_id": "232323",
                "paternal_genotype": "Ai93(TITL-GCaMP6f)/wt",
            },
            "housing": {
                "object_type": "Housing",
                "cage_id": "123",
                "home_cage_enrichment": ["Running wheel"],
                "cohoused_subjects": [],
            },
            "source": {
                "name": "Allen Institute",
                "abbreviation": "AI",
                "registry": "Research Organization Registry (ROR)",
                "registry_identifier": "03cpe7c52",
            },
            "restrictions": None,
        },
        "notes": None,
    }
    return sample_subject


@mcp.tool()
def get_processing_example():
    """
    Example of the processing schema (V2).
    Contains 'data_processes' and 'pipelines' lists, plus a 'dependency_graph'.
    Each data process has a 'code' object (not a list) and a 'pipeline_name'.
    Access fields like this - processing.<field_name>
    """
    sample_processing = {
        "object_type": "Processing",
        "schema_version": "2.3.0",
        "data_processes": [
            {
                "object_type": "Data process",
                "process_type": "Image tile fusing",
                "name": "Image tile fusing",
                "stage": "Processing",
                "pipeline_name": "Imaging processing pipeline",
                "code": {
                    "object_type": "Code",
                    "url": "https://github.com/abcd",
                    "version": "0.1",
                    "parameters": {"size": 7},
                },
                "experimenters": ["Dr. Dan"],
                "start_date_time": "2022-11-22T08:43:00Z",
                "end_date_time": "2022-11-22T08:43:00Z",
                "output_path": "path/to/outputs",
                "notes": None,
            },
            {
                "object_type": "Data process",
                "process_type": "File format conversion",
                "name": "File format conversion",
                "stage": "Processing",
                "pipeline_name": "Imaging processing pipeline",
                "code": {
                    "object_type": "Code",
                    "url": "https://github.com/abcd",
                    "version": "0.1",
                    "parameters": {"u": 7, "z": True},
                },
                "experimenters": ["Dr. Dan"],
                "start_date_time": "2022-11-22T08:43:00Z",
                "end_date_time": "2022-11-22T08:43:00Z",
                "output_path": "path/to/outputs",
                "notes": None,
            },
        ],
        "pipelines": [
            {
                "object_type": "Code",
                "url": "https://url/for/pipeline",
                "name": "Imaging processing pipeline",
                "version": "0.1.1",
                "input_data": [{"object_type": "Data asset", "name": "123456_2026-05-20_14-14-14", "url": None}],
            }
        ],
        "dependency_graph": {
            "Image tile fusing": [],
            "File format conversion": ["Image tile fusing"],
        },
        "notes": None,
    }
    return sample_processing


@mcp.tool()
def get_model_example() -> dict:
    """
    Example of the model schema (V2).
    Describes a machine learning model including architecture, training, and evaluation.
    training and evaluations are lists of ModelTraining/ModelEvaluation (subclass of DataProcess).
    Access fields like this - model.<field_name>
    """
    sample_model = {
        "object_type": "Model",
        "schema_version": "2.0.0",
        "name": "2024_01_01_ResNet18_SmartSPIM",
        "version": "0.1",
        "architecture": "ResNet",
        "software_framework": {"object_type": "Software", "name": "tensorflow", "version": "2.11.0"},
        "architecture_parameters": {"layers": 18, "input_shape": [14, 14, 26]},
        "intended_use": "Cell counting for 488 channel of SmartSPIM data",
        "limitations": "Only trained on 488 channel",
        "example_run_code": {
            "object_type": "Code",
            "url": "url for model code repo",
            "run_script": "predict.py",
        },
        "training": [
            {
                "object_type": "Model training",
                "process_type": "Model training",
                "name": "Model training",
                "stage": "Processing",
                "code": {
                    "object_type": "Code",
                    "url": "url for model code repo",
                    "run_script": "train.py",
                    "input_data": [{"object_type": "Data asset", "url": "s3 path to training data"}],
                    "parameters": {"learning_rate": 0.0001, "batch_size": 32, "augmentation": True},
                },
                "experimenters": ["Dr. Dan"],
                "output_path": "trained_model.h5",
                "notes": "note on training data selection",
                "train_performance": [
                    {"object_type": "Performance metric", "name": "precision", "value": 0.9},
                    {"object_type": "Performance metric", "name": "recall", "value": 0.85},
                ],
                "test_performance": [
                    {"object_type": "Performance metric", "name": "precision", "value": 0.8},
                    {"object_type": "Performance metric", "name": "recall", "value": 0.8},
                ],
                "test_evaluation_method": "random 4:1 train/test split",
            }
        ],
        "evaluations": [
            {
                "object_type": "Model evaluation",
                "process_type": "Model evaluation",
                "name": "Model evaluation",
                "stage": "Processing",
                "code": {
                    "object_type": "Code",
                    "url": "url for model code repo",
                    "run_script": "eval.py",
                    "input_data": [{"object_type": "Data asset", "url": "s3 path to eval data"}],
                },
                "experimenters": ["Dr. Dan"],
                "performance": [{"object_type": "Performance metric", "name": "precision", "value": 0.8}],
            }
        ],
        "notes": None,
    }
    return sample_model

