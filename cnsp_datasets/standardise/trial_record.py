from typing import Callable, Any, List
from mne.io import BaseRaw


class StimulusRecord:
    def __init__(
            self,
            modality: str,
            name: str,
            data_fn: Callable[[], Any],
            is_attended: bool = False,
            feature_name: str | None = None
            ):
        
        self.modality = modality
        self.name = name
        self.data_fn = data_fn
        self.is_attended = is_attended

        # some datasets only provide the envelope etc rather than full audio
        self.feature_name = feature_name if feature_name is not None else modality


class TrialRecord:

    def __init__(
            self,
            subject: int,
            session: int,
            trial: int,
            condition: str,
            ns_type: str,
            stimulus: StimulusRecord | List[StimulusRecord],
            neural_data_fn: Callable[[], BaseRaw],
            structural_data_fn: Callable[[], Any] | None = None,
            behavioural_data_fn: Callable[[], Any] | None = None,
    ):
        
        self.subject = subject
        self.session = session
        self.trial = trial
        self.condition = condition
        self.ns_type = ns_type

        self.stimulus = stimulus if isinstance(stimulus, list) else [stimulus]

        self._neural_data_fn = neural_data_fn
        self._structural_data_fn = structural_data_fn
        self._behavioural_data_fn = behavioural_data_fn

    @property
    def neural_data(self) -> BaseRaw:
        return self._neural_data_fn()
    
    @property
    def structural_data(self) -> Any | None:
        if self._structural_data_fn is not None:
            return self._structural_data_fn()
        else:
            raise ValueError("No structural data function provided.")
        
    @property
    def behavioural_data(self) -> Any | None:
        if self._behavioural_data_fn is not None:
            return self._behavioural_data_fn()
        else:
            raise ValueError("No behavioural data function provided.")