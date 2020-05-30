import torch
from efficientnet_pytorch import EfficientNet
import pandas as pd
import numpy as np

class CustomEnsemble(torch.nn.Module):

    def __init__(self, name, num_classes):
        super(CustomEnsemble, self).__init__()
        torch.cuda.manual_seed(10)
        self.m0 = EfficientNet.from_pretrained(name, num_classes=num_classes)
        torch.cuda.manual_seed(80131)
        self.m1 = EfficientNet.from_pretrained(name, num_classes=num_classes)
        torch.cuda.manual_seed(9183120)
        self.m2 = EfficientNet.from_pretrained(name, num_classes=num_classes)
        torch.cuda.manual_seed(1231)
        self.m3 = EfficientNet.from_pretrained(name, num_classes=num_classes)

    def forward(self, x):

        y0 = self.m0(x.clone()).unsqueeze(0)
        y1 = self.m1(x.clone()).unsqueeze(0)
        y2 = self.m2(x.clone()).unsqueeze(0)
        y3 = self.m3(x.clone()).unsqueeze(0)

        y = torch.cat((y0, y1, y2, y3))

        mean =  torch.mean(y, dim=0)

        return mean

def train(title:str, model :torch.nn.Module, dataset: torch.utils.data.Dataset, epochs: int, batch:int,  device:torch.device):
    # Cross Entropy Loss plays the same role as Softmax loss (multiclass regression)
    # With this we got two classes: {FAKE, REAL}. An the algorithm should spit the probablities.
    criterion = torch.nn.CrossEntropyLoss(weight=None, reduction='mean').to(device)
    # optim.SGD(net.parameters(), lr=.0002, amsgrad=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=.0002, amsgrad=True)

    loader = torch.utils.data.DataLoader(dataset, batch_size=batch)

    for epoch in range(epochs):

        running_loss = []

        for idx, data in enumerate(loader, 0):
            # Get the inputs and labels
            inputs, labels = data[0].to(device), data[1].to(device)
            # zero the parameter gradients
            optimizer.zero_grad()
            # forward + backward + optimize
            outputs = model(inputs)
            #print(inputs.size(), labels.size(), outputs.size())
            loss = criterion(outputs, labels)
            loss.backward()
            # print statistics
            running_loss.append(loss.item())
            optimizer.step()

        mean_loss = np.mean(running_loss)
        print(f'Epoch {epoch} - loss {mean_loss}')

    print(f'{title} finished training')


def test(model :torch.nn.Module, dataset: torch.utils.data.Dataset, device:torch.device, path:str):
    # Cross Entropy Loss plays the same role as Softmax loss (multiclass regression)
    # With this we got two classes: {FAKE, REAL}. An the algorithm should spit the probablities.
    criterion = torch.nn.CrossEntropyLoss(weight=None).to(device)

    loader = torch.utils.data.DataLoader(dataset, batch_size=1)

    running_loss = .0

    df = pd.read_csv('datasets/ob_dataset.csv')
    videos = df.video.tolist()
    paths = df.path.tolist()

    rows = []

    with torch.no_grad():

        for idx, data in enumerate(loader, 0):
            # Get the inputs and labels
            inputs, labels = data[0].to(device), data[1].to(device)
            # zero the parameter gradients
            # forward + backward + optimize
            outputs = model(inputs)
            max, index = outputs.max(1)
            loss = criterion(outputs, labels)
            real_score = outputs[0, 0].item()
            fake_score = outputs[0, 1].item()
            fake_prob = np.exp(fake_score) / (np.exp(fake_score) + np.exp(real_score))
            row =(videos[idx], paths[idx], labels.item(), index.item(), loss.item(),
                  outputs[0, 0].item(), outputs[0, 1].item(), fake_prob)
            rows.append(row)
            # print statistics
            running_loss += loss.item()

        # Print results at the end of the epoch
        print('Finished Testing prediction of Model.')
        print('Total execution', running_loss / idx)

    res = pd.DataFrame(rows, columns = ('video', 'path', 'label', 'predicted', 'loss', 'score_real', 'score_fake', 'fake_prob'))
    res.to_csv(path, index = False)