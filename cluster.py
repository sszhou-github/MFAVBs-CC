import os
import argparse
import torch
import torchvision
import numpy as np
from utils import yaml_config_hook, generate_random_number
from modules import network, transform, vtcc
from evaluation import evaluation
from torch.utils import data
import copy
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import pandas as pd
import random

def inference(loader, model, device):
    model.eval()
    feature_vector = []
    labels_vector = []
    for step, (x, y, a) in enumerate(loader):
        X_ii = torch.tensor([]).to('cuda')
        for (i, j) in enumerate(a):
            j = j.replace("/datasets/", "/data/")
            j = j.replace(".jpg", ".pt")
            x_ii = torch.load(j)
            X_ii = torch.cat((X_ii, x_ii), dim=0)
        x = x.to(device)
        with torch.no_grad():
            c = model.forward_cluster(x, X_ii)
        c = c.detach()
        feature_vector.extend(c.cpu().detach().numpy())
        labels_vector.extend(y.numpy())
        if step % 20 == 0:
            print(f"Step [{step}/{len(loader)}]\t Computing features...")
    feature_vector = np.array(feature_vector)
    labels_vector = np.array(labels_vector)
    print("Features shape {}".format(feature_vector.shape))
    return feature_vector, labels_vector


if __name__ == "__main__":
    random_number = generate_random_number()
    parser = argparse.ArgumentParser()
    config = yaml_config_hook("rh2/config/config.yaml")
    for k, v in config.items():
        parser.add_argument(f"--{k}", default=v, type=type(v))
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if args.dataset == "RSOD":
        dataset = torchvision.datasets.ImageFolder(
            root='./datasets/RSOD',
            transform=transform.Augmentation(size=args.image_size).test_transform,
        )
        class_num = 4
    elif args.dataset == "UC-Merced":
        dataset = torchvision.datasets.ImageFolder(
            root='./datasets/UC-Merced',
            transform=transform.Augmentation(size=args.image_size),
            #transform=transform.Augmentation(size=args.image_size).test_transform,
        )
        class_num = 21
    elif args.dataset == "SIRI-WHU":
        dataset = torchvision.datasets.ImageFolder(
            root='./datasets/SIRI-WHU',
            transform=transform.Augmentation(size=args.image_size).test_transform,
        )
        class_num = 12
    elif args.dataset == "AID":
        dataset = torchvision.datasets.ImageFolder(
            root='./datasets/AID',
            transform=transform.Augmentation(size=args.image_size).test_transform,
        )
        class_num = 30
    elif args.dataset == "D0":
        dataset = torchvision.datasets.ImageFolder(
            root='./datasets/D0',
            transform=transform.Augmentation(size=args.image_size).test_transform,
        )
        class_num = 40
    elif args.dataset == "DTD":
        dataset = torchvision.datasets.ImageFolder(
            root='./datasets/DTD',
            transform=transform.Augmentation(size=args.image_size).test_transform,
        )
        class_num = 47
    elif args.dataset == "Chaoyang":
        dataset = torchvision.datasets.ImageFolder(
            root='./datasets/Chaoyang',
            transform=transform.Augmentation(size=args.image_size).test_transform,
        )
        class_num = 4

    elif args.dataset == "CIFAR-100":
        train_dataset = torchvision.datasets.CIFAR100(
            root="./datasets",
            download=True,
            train=True,
            transform=transform.Augmentation(size=args.image_size).test_transform,
        )
        test_dataset = torchvision.datasets.CIFAR100(
            root="./datasets",
            download=True,
            train=False,
            transform=transform.Augmentation(size=args.image_size).test_transform,
        )
        dataset = data.ConcatDataset([train_dataset, test_dataset])
        class_num = 20
    else:
        raise NotImplementedError
    
    data_loader = torch.utils.data.DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        drop_last=False,
        num_workers=args.workers,
    )

    vtcc = vtcc.vit_small()
    model = network.Network_VTCC(vtcc, args.feature_dim, class_num)
    model = model.to('cuda')

    model_fp = os.path.join(args.model_path, "checkpoint_{}.tar".format(400))
    model.load_state_dict(torch.load(model_fp, map_location=device.type)['net'])
    '''
    for name, param in model.named_parameters():
          print(name)
    exit()
    '''
    model.to(device)

    print("### Creating features from model ###")
    X, Y = inference(data_loader, model, device)
    #x = pd.DataFrame(x)

    if args.dataset == "CIFAR-100":  # super-class
        super_label = [
            [72, 4, 95, 30, 55],
            [73, 32, 67, 91, 1],
            [92, 70, 82, 54, 62],
            [16, 61, 9, 10, 28],
            [51, 0, 53, 57, 83],
            [40, 39, 22, 87, 86],
            [20, 25, 94, 84, 5],
            [14, 24, 6, 7, 18],
            [43, 97, 42, 3, 88],
            [37, 17, 76, 12, 68],
            [49, 33, 71, 23, 60],
            [15, 21, 19, 31, 38],
            [75, 63, 66, 64, 34],
            [77, 26, 45, 99, 79],
            [11, 2, 35, 46, 98],
            [29, 93, 27, 78, 44],
            [65, 50, 74, 36, 80],
            [56, 52, 47, 59, 96],
            [8, 58, 90, 13, 48],
            [81, 69, 41, 89, 85],
        ]
        Y_copy = copy.copy(Y)
        for i in range(20):
            for j in super_label[i]:
                Y[Y_copy == j] = i
    nmi, ari, f, acc = evaluation.evaluate(Y, X)
    print('NMI = {:.4f} ARI = {:.4f} F = {:.4f} ACC = {:.4f}'.format(nmi, ari, f, acc))
    '''
    Y = pd.DataFrame(Y)
    X = pd.DataFrame(X)
    X.to_excel('2.xlsx')
    Y.to_excel('3.xlsx')

    # 使用t-SNE进行降维
    tsne = TSNE(n_components=2, random_state=0)

    # 现在可以使用t-SNE对X_flattened进行降维
    X_2d = tsne.fit_transform(x)
    df = pd.DataFrame()
    plt.figure(figsize=(6, 5))
    for i in range(4):
        indices = [index for index, value in enumerate(Y) if value == i]
        plt.scatter(X_2d[indices,0], X_2d[indices,1], label = i+1, s = 5)
        df = pd.concat([df,pd.DataFrame(X_2d[indices,:])])
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    plt.savefig('1.png')
    plt.show()
    #df.to_excel('VTCCtrain/output1.xlsx')

    '''