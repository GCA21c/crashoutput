from dataclasses import asdict, dataclass, field


@dataclass
class ParsedIsoCode:
    raw_code: str = ''
    matched_code: str = ''
    source: str = ''
    parse_mode: str = ''
    parse_confidence: float = 0.0
    dummy_position_raw: str = ''
    dummy_position_normalized: str = ''
    mount_type: str = ''
    main_location_code: str = ''
    fine_location_1: str = ''
    fine_location_2: str = ''
    redundant_index: str = ''
    dummy_type_code: str = ''
    dummy_type_label: str = ''
    data_type_code: str = ''
    data_type_label: str = ''
    axis_code: str = ''
    axis_label: str = ''
    filter_code_source: str = ''
    filter_label_source: str = ''
    sensor_location: str = ''
    side: str = ''
    level: str = ''
    position_detail: str = ''
    tokens: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)
