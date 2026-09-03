from satquery.router import route
from satquery.schemas import Modality, TaskType


def test_landcover_routing():
    p = route("What land cover types are in this image?", [Modality.OPTICAL])
    assert p.task == TaskType.LANDCOVER and p.tool == "landcover"


def test_change_routing_needs_two_images():
    p = route("What changed between these two dates?",
              [Modality.OPTICAL, Modality.OPTICAL])
    assert p.task == TaskType.CHANGE and p.tool == "change_detect"


def test_change_with_one_image_diverts_to_vqa_with_warning():
    p = route("What changed between these two dates?", [Modality.OPTICAL])
    assert p.task == TaskType.VQA
    assert "two images" in p.notes


def test_xmodal_routes_on_sar_keyword():
    p = route("The optical image is cloudy — what does SAR show underneath?",
              [Modality.PAIR])
    assert p.task == TaskType.XMODAL


def test_xmodal_without_pair_diverts():
    p = route("What does the SAR show under the clouds?", [Modality.OPTICAL])
    assert p.task == TaskType.VQA
    assert "cross-modal" in p.notes.lower()


def test_ground_routing():
    p = route("Locate the largest building.", [Modality.OPTICAL])
    assert p.task == TaskType.GROUND


def test_segment_routing():
    p = route("Segment the water across optical and radar.", [Modality.PAIR])
    assert p.task == TaskType.XMODAL_MASK


def test_caption_routing():
    p = route("Describe this scene.", [Modality.OPTICAL])
    assert p.task == TaskType.CAPTION


def test_default_question_goes_to_vqa_baseline():
    p = route("Roughly how many buildings are visible?", [Modality.OPTICAL])
    assert p.task == TaskType.VQA


def test_modality_detection_pair():
    from satquery.router import detect_modalities
    present = detect_modalities([Modality.OPTICAL, Modality.SAR])
    assert Modality.PAIR in present
