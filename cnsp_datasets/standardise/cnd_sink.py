import numpy as np
from pathlib import Path
from scipy.io import savemat, loadmat
from cnsp_datasets.standardise.trial_record import TrialRecord


def _cell_row_from_list(objs):
    """Return a 1xN object array suitable for MATLAB cell arrays."""
    cell = np.empty((1, len(objs)), dtype=object)
    for i, o in enumerate(objs):
        cell[0, i] = np.array(o)
    return cell

def _append_cell_row(existing_cell, new_obj):
    """Append new_obj to a 1xN object array and return a new 1x(N+1) cell."""
    # existing_cell may be (N,) or (1,N) depending on how it was created/loaded
    arr = np.asarray(existing_cell, dtype=object)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    out = np.empty((1, arr.shape[1] + 1), dtype=object)
    out[0, :arr.shape[1]] = arr[0, :]
    out[0, -1] = np.array(new_obj)
    return out

def _to_list_1d(x):
    """
    Convert MATLABy arrays (1xN cell or char cell) to a flat Python list.
    Works if x is already a Python list, a numpy 1-D array, or (1,N)/(N,) object arrays.
    """
    if isinstance(x, list):
        return x
    a = np.atleast_1d(x)
    # flatten 1xN to (N,)
    if a.ndim > 1:
        a = a.ravel(order="C")
    return a.tolist()


class CNDSinkV1:
    def __init__(self, save_directory):
        self.save_directory = Path(save_directory)
        if not self.save_directory.exists():
            self.save_directory.mkdir(parents=True, exist_ok=True)

    def save_record(self, record: TrialRecord):
        # try:
        self._save(record)
        # except Exception as e:
        #     print(f"Error saving record {record}: {e}")
        #     return

    def _save(self, record: TrialRecord):
        sub = record.subject
        raw = record.neural_data

        trial_data = dict(
            data=raw.get_data(),
            fs=raw.info['sfreq'],
            ch_names=raw.info['ch_names'],
            origTrialPosition=record.trial,
            cndVersion="1.0",
        )

        subFile = self.save_directory / f"dataSub{sub}.mat"
        self._save_neural_data_to_mat(subFile, trial_data)

        for stim_record in record.stimulus:
            if stim_record.modality != "audio":
                continue  # only save audio stimuli for now

            stimulus_dict = stim_record.stim_data
            if stimulus_dict["data"] is None:
                continue

            stim_data = dict(
                name=stim_record.feature_name,
                fs=stimulus_dict['fs'],
                data=stimulus_dict['data'],
                condName=record.condition,
                cndVersion="1.0",
                stimId=stim_record.name
            )
            stimFile = self.save_directory / f"dataStim{sub}_{stim_record.feature_name}.mat"
            self._save_stimuli_to_mat(stimFile, stim_data)

    # ------------------------------
    # Stimuli
    # ------------------------------
    def _save_stimuli_to_mat(self, stimFile, stim_data):
        if not stimFile.exists():
            data_to_save = {
                'names': [stim_data['name']],              # -> cellstr in MATLAB
                'data': _cell_row_from_list([stim_data['data']]),
                'stimIdxs': [1],                           # numeric vector
                'condIdxs': [1],
                'condNames': [stim_data['condName']],      # -> cellstr
                'cndVersion': stim_data['cndVersion'],
                'stimIds': [stim_data['stimId']],          # -> cellstr
                'conditions': [stim_data['condName']],     # (dup of condNames per your schema)
                'fs': [stim_data['fs']],                   # keep fs alongside if needed
            }
            savemat(str(stimFile), data_to_save)
            return

        # Append to existing
        loaded = loadmat(str(stimFile), squeeze_me=False, struct_as_record=False)

        # Grow the cell array of data
        old_cell = loaded['data']          # expected 1xN object array
        new_cell = _append_cell_row(old_cell, stim_data['data'])

        # Handle indices and label lists (MATLAB 1-based)
        all_stimIds = _to_list_1d(loaded['stimIds'])
        all_stimIds.append(stim_data['stimId'])
        stimIdx = all_stimIds.index(stim_data['stimId']) + 1  # 1-based

        condNames = _to_list_1d(loaded['condNames'])
        if stim_data['condName'] not in condNames:
            condNames.append(stim_data['condName'])
        condIdx = condNames.index(stim_data['condName']) + 1

        condIdxs = _to_list_1d(loaded['condIdxs'])
        condIdxs.append(condIdx)

        conditions = _to_list_1d(loaded['conditions'])
        conditions.append(stim_data['condName'])

        names = _to_list_1d(loaded['names'])
        # If each entry corresponds to a trial instance name, you may want to append here too.
        # If not, keep as-is. Uncomment if appropriate:
        # names.append(stim_data['name'])

        data_to_save = {
            'names': names,
            'data': new_cell,
            'stimIdxs': _to_list_1d(loaded['stimIdxs']) + [stimIdx],
            'condIdxs': condIdxs,
            'condNames': condNames,
            'cndVersion': "1.0",
            'stimIds': all_stimIds,
            'conditions': conditions,
            'fs': _to_list_1d(loaded.get('fs', [])) + [stim_data['fs']],
        }
        savemat(str(stimFile), data_to_save)

    # ------------------------------
    # Neural data
    # ------------------------------
    def _save_neural_data_to_mat(self, subFile, trial_data):
        if not subFile.exists():
            # Create new file
            out = dict(trial_data)
            out['data'] = _cell_row_from_list([trial_data['data']])
            # ch_names -> cellstr in MATLAB
            out['ch_names'] = _to_list_1d(trial_data['ch_names'])
            out['origTrialPosition'] = [trial_data['origTrialPosition']]
            savemat(str(subFile), out)
            return

        # Append
        loaded = loadmat(str(subFile), squeeze_me=False, struct_as_record=False)

        # Grow the cell array (FIX: append the NEW trial, not the old cell)
        old_cell = loaded['data']
        new_cell = _append_cell_row(old_cell, trial_data['data'])

        # Extend simple vectors/lists
        orig_positions = _to_list_1d(loaded.get('origTrialPosition', []))
        orig_positions.append(trial_data['origTrialPosition'])

        out = dict(loaded)  # start from loaded keys, then overwrite the ones we maintain
        out['data'] = new_cell
        out['origTrialPosition'] = orig_positions
        out['fs'] = loaded.get('fs', trial_data['fs'])
        out['ch_names'] = _to_list_1d(loaded.get('ch_names', trial_data['ch_names']))
        out['cndVersion'] = "1.0"

        # Remove MATLAB housekeeping keys that loadmat adds
        for k in list(out.keys()):
            if k.startswith('__'):
                del out[k]

        savemat(str(subFile), out)



# import numpy as np

# from pathlib import Path
# from scipy.io import savemat, loadmat
# from cnsp_datasets.standardise.trial_record import TrialRecord


# class CNDSinkV1:
#     def __init__(self, save_directory):

#         self.save_directory = Path(save_directory)
#         if not self.save_directory.exists():
#             self.save_directory.mkdir(parents=True, exist_ok=True)

#     def save_record(self, record: TrialRecord):

#         # try:
#         self._save(record)
#         # except Exception as e:
#         #     print(f"Error saving record {record}: {e}")
#         #     return
        
#     def _save(self, record: TrialRecord):

#         sub = record.subject
#         raw = record.neural_data

#         trial_data = dict(
#             data = raw.get_data(),
#             fs = raw.info['sfreq'],
#             ch_names = raw.info['ch_names'],
#             origTrialPosition = record.trial,
#             # chanlocs = [],
#             # extchan = [],
#             cndVersion = "1.0"
#         )

#         subFile = self.save_directory / f"dataSub{sub}.mat"
#         self._save_neural_data_to_mat(subFile, trial_data)

#         for stim_record in record.stimulus:

#             if stim_record.modality != "audio":
#                 continue # only save audio stimuli for now
            
#             stimulus_dict = stim_record.stim_data
#             if stimulus_dict["data"] is None:
#                 continue
#             print(stimulus_dict)

#             stim_data = dict(
#                 name = stim_record.feature_name,
#                 fs = stimulus_dict['fs'],
#                 data = stimulus_dict['data'],
#                 condName = record.condition,
#                 cndVersion = "1.0",
#                 stimId = stim_record.name
#             )
#             stimFile = self.save_directory / f"dataStim{sub}_{stim_record.feature_name}.mat"
#             self._save_stimuli_to_mat(stimFile, stim_data)


#     def _save_stimuli_to_mat(self, stimFile, stim_data):

#         if not stimFile.exists():

#             cell_data = np.empty((1,), dtype=object)
#             cell_data[0] = np.array(stim_data['data'])

#             data_to_save = {
#                 'names': [stim_data['name']],
#                 'data': cell_data,
#                 'stimIdxs' : [1],
#                 'condIdxs' : [1],
#                 'condNames' : [stim_data['condName']],
#                 'cndVersion': stim_data['cndVersion'],

#                 'stimIds': [stim_data['stimId']],
#                 'conditions': [stim_data['condName']],
#             }
#             savemat(str(stimFile), data_to_save)

#         else:
#             loaded_stim_data = loadmat(str(stimFile))
            
#             stimId = stim_data['stimId']
#             all_stimIds  = loaded_stim_data['stimIds'].tolist()
#             if type(all_stimIds) == str:
#                 all_stimIds = [all_stimIds]
#             all_stimIds.append(stimId)
#             stimIdx = all_stimIds.index(stimId) + 1

#             conditions = loaded_stim_data['conditions'].tolist()
#             condNames = loaded_stim_data['condNames'].tolist()
#             if stim_data['condName'] not in condNames:
#                 condNames.append(stim_data['condName'])
#             condIdx = condNames.index(stim_data['condName']) + 1

#             conditions.append(stim_data['condName'])
#             condIdxs = loaded_stim_data['condIdxs'].tolist() + [condIdx]

#             import pdb;pdb.set_trace()
#             data_cell = np.empty((loaded_stim_data["data"].shape[1] + 1,), dtype=object)
#             for i, d in enumerate(loaded_stim_data["data"][0, :]):
#                 data_cell[i] = np.array(d)
#             data_cell[-1] = np.array(stim_data['data'])

#             data_to_save = {
#                 'names': loaded_stim_data['names'],
#                 'data': data_cell,
#                 'stimIdxs' : loaded_stim_data['stimIdxs'].tolist() + [stimIdx],
#                 'condIdxs' : condIdxs,
#                 'condNames' : condNames,
#                 'cndVersion': "1.0",
#                 'stimIds': all_stimIds,
#                 'conditions': conditions
#             }

#             #import pdb;pdb.set_trace()
 
#             savemat(str(stimFile), data_to_save)

#     def _save_neural_data_to_mat(self, subFile, trial_data):

#         if not subFile.exists():
#             # Create new file
#             cell_data = np.empty((1,), dtype=object)
#             cell_data[0] = np.array(trial_data['data'])
#             trial_data['data'] = cell_data
#             savemat(str(subFile), trial_data)
#         else:
#             # Append to existing file
#             original_sub_data = loadmat(subFile)

#             data_cell = np.empty((original_sub_data["data"].shape[1] + 1,), dtype=object)
#             for i, d in enumerate(original_sub_data["data"][0, :]):
#                 data_cell[i] = np.array(d)
#             data_cell[-1] = np.array(original_sub_data['data'])

#             trial_data["data"] = data_cell
#             trial_data["origTrialPosition"] = [x for x in original_sub_data["origTrialPosition"]] + [trial_data["origTrialPosition"]]

#             savemat(str(subFile), trial_data)