import pickle
from pathlib import Path

DATASET_EXT = '.pkl'


class DatasetStoreError(Exception):
    pass


def save_dataset_pickle(file_path, dataframe, metadata=None, history=None, source_file_path=None, source_label=None):
    path = Path(file_path)
    payload = {
        'dataframe': dataframe,
        'metadata': dict(metadata or {}),
        'history': list(history or []),
        'source_file_path': source_file_path,
        'source_label': source_label,
        'format': 'CRASH_ANALYSIS_PICKLE_V1',
    }
    with path.open('wb') as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    return str(path)


def load_dataset_pickle(file_path):
    path = Path(file_path)
    try:
        with path.open('rb') as f:
            payload = pickle.load(f)
    except Exception as e:
        raise DatasetStoreError(f'임시 데이터 파일을 읽지 못했습니다: {e}') from e

    if not isinstance(payload, dict) or 'dataframe' not in payload:
        raise DatasetStoreError('지원하지 않는 임시 데이터 파일 형식입니다.')

    return {
        'dataframe': payload['dataframe'],
        'metadata': dict(payload.get('metadata') or {}),
        'history': list(payload.get('history') or []),
        'source_file_path': payload.get('source_file_path'),
        'source_label': payload.get('source_label'),
    }
