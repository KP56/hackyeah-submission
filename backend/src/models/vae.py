# vae.py
import torch
import torch.nn as nn
import torch.optim as optim

class VAE(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, latent_dim: int, kl_weight: float = 1.0):
        super(VAE, self).__init__()
        self.kl_weight = kl_weight

        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU()
        )
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)

        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
            nn.Sigmoid()  # assuming input normalized between 0 and 1
        )

        self.optimizer = optim.SGD(self.parameters(), lr=0.01)

    def encode(self, x):
        h = self.encoder(x)
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        return mu, logvar

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z):
        return self.decoder(z)

    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        recon_x = self.decode(z)
        return recon_x, mu, logvar

    def mahalanobis_distance(self, x, y):
        """
        Computes Mahalanobis distance between x and y (batch-wise)
        :param x: torch.Tensor of shape [batch_size, dim]
        :param y: torch.Tensor of shape [batch_size, dim]
        """
        delta = x - y
        cov = torch.cov(delta.T) + 1e-5 * torch.eye(delta.shape[1])  # regularization
        cov_inv = torch.linalg.pinv(cov)
        m_dist = torch.sqrt(torch.sum(delta @ cov_inv * delta, dim=1))
        return m_dist

    def loss_function(self, recon_x, x, mu, logvar):
        # Reconstruction using Mahalanobis distance
        m_dist = self.mahalanobis_distance(recon_x, x)
        recon_loss = torch.sum(m_dist)  # sum over batch

        # KL divergence
        kl_div = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())

        return recon_loss + self.kl_weight * kl_div

    def train_step(self, x_batch):
        """
        Performs one SGD update using a batch of vectors.
        :param x_batch: torch.Tensor of shape [batch_size, input_dim]
        """
        self.train()
        self.optimizer.zero_grad()

        recon_x, mu, logvar = self.forward(x_batch)
        loss = self.loss_function(recon_x, x_batch, mu, logvar)
        loss.backward()
        self.optimizer.step()

        return loss.item()
