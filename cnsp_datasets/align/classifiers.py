import torch
import torch.nn as nn

class SimilarityDetector(nn.Module):

    def __init__(self,
                 n_eeg_channels=64,
                 n_stimfeat_channels=1,
                 n_layers=3,
                 kernel_size=3,
                 spatial_filters=8,
                 dilation_filters=16):
        
        super().__init__()

        self.n_layers = n_layers

        self.eeg_spatial_filter = nn.Conv1d(n_eeg_channels, spatial_filters, kernel_size=1, bias=False)

        self.eeg_projections = nn.ModuleList(
            [nn.Conv1d(spatial_filters, dilation_filters, kernel_size=kernel_size, groups=spatial_filters)] +\
                  [nn.Conv1d(dilation_filters, dilation_filters,kernel_size=kernel_size, dilation=kernel_size**(i+1)) for i in range(n_layers-1)]
                  )
        
        self.stimfeat_projections = nn.ModuleList(
            [nn.Conv1d(n_stimfeat_channels, dilation_filters, kernel_size=kernel_size)] +\
                  [nn.Conv1d(dilation_filters, dilation_filters,kernel_size=kernel_size, dilation=kernel_size**(i+1)) for i in range(n_layers-1)]
        )

        self.activation = nn.ReLU()

        self.linear = nn.Linear(dilation_filters**2, 1, bias=False)

    def forward(self, eeg, stim):


        eeg = self.eeg_spatial_filter(eeg)

        for i in range(self.n_layers):

            eeg = self.eeg_projections[i](eeg)
            stim = self.stimfeat_projections[i](stim)

            eeg = self.activation(eeg)
            stim = self.activation(stim)

        eeg = nn.functional.normalize(eeg, dim=-1)        
        stim = nn.functional.normalize(stim, dim=-1)

        inner = eeg @ torch.transpose(stim, 1, 2)

        
        out = self.linear(
            inner.flatten(start_dim=1)
            )

        return out