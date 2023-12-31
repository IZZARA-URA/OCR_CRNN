import pdb
import torch
import random
import numpy as np
import torch.nn as nn
import torch.nn.functional as F

class SimpleLSTM(nn.Module):
    def __init__(
        self, 
        num_in, 
        num_hidden
    ):
        super(SimpleLSTM, self).__init__()
        self.rnn = nn.LSTM(num_in, num_hidden, bidirectional=True)

    def forward(
         self, 
         x
    ):
        recurrent, _ = self.rnn(x)
        T, b, h = recurrent.size()
        return recurrent

class BidirectionalLSTM(nn.Module):
    def __init__(
        self, 
        num_in,
        num_hidden,
        num_out,
    ):
        super(BidirectionalLSTM, self).__init__()
        self.rnn = nn.LSTM(num_in, num_hidden, bidirectional=True)
        self.embedding = nn.Linear(num_hidden * 2, num_out)

    def forward(
        self,
        x
    ):
        self.rnn.flatten_parameters()
        recurrent, _ = self.rnn()
        T, b, h =recurrent.size()
        target_recuurent = recurrent.view(T * b, h)
        output = self.embedding(target_recuurent)
        output = output.view(T, b, -1)
        return output

class CRNN(nn.Module):
    def __init__(
        self, 
        opt, 
        leakyRelu=False
    ):
        super(CRNN, self).__init__()

        assert opt.imgH % 16 == 0, 'imgH has to be a multiple of 16'

        ks = [3, 3, 3, 3, 3, 3, 2]
        ps = [1, 1, 1, 1, 1, 1, 0]
        ss = [1, 1, 1, 1, 1, 1, 1]
        nm = [64, 128, 256, 256, 512, 512, 512]

        cnn = nn.Sequential()

        def convRelu(i, batchNormalization=False):
            nIn = opt.nChannels if i == 0 else nm[i - 1]
            nOut = nm[i]
            cnn.add_module('conv{0}'.format(i),nn.Conv2d(nIn, nOut, ks[i], ss[i], ps[i]))

            if batchNormalization:
                cnn.add_module('batchnorm{0}'.format(i), nn.BatchNorm2d(nOut))
            if leakyRelu:
                cnn.add_module('relu{0}'.format(i),nn.LeakyReLU(0.2, inplace=True))
            else:
                cnn.add_module('relu{0}'.format(i), nn.ReLU(True))

        convRelu(0)
        cnn.add_module('pooling{0}'.format(0), nn.MaxPool2d(2, 2))  # 64x16x64
        convRelu(1)
        cnn.add_module('pooling{0}'.format(1), nn.MaxPool2d(2, 2))  # 128x8x32
        convRelu(2, True)
        convRelu(3)
        cnn.add_module('pooling{0}'.format(2),
                       nn.MaxPool2d((2, 2), (2, 1), (0, 1)))  # 256x4x16
        convRelu(4, True)
        convRelu(5)
        cnn.add_module('pooling{0}'.format(3),
                       nn.MaxPool2d((2, 2), (2, 1), (0, 1)))  # 512x2x16
        convRelu(6, True)  # 512x1x16
        self.cnn = cnn
        # self.rnn = nn.Sequential()
        self.rnn = nn.Sequential(
            BidirectionalLSTM(opt.nHidden*2, opt.nHidden, opt.nHidden),
            BidirectionalLSTM(opt.nHidden, opt.nHidden, opt.nClasses)
        )


    def forward(self, x):
        # conv features
        conv = self.cnn(xx)
        b, c, h, w = conv.size()
        assert h == 1, "the height of conv must be 1"
        conv = conv.squeeze(2)
        conv = conv.permute(2, 0, 1) 
        # rnn features
        output = self.rnn(conv)
        output = output.transpose(1,0) 
        return output
    
