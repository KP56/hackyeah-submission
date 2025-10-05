import numpy as np
from sklearn.cluster import KMeans
from scipy.spatial.distance import cdist


class Clustering:
    """
    Clustering class that performs KMeans on vectors from a VectorRegistry.
    It can measure distance of new vectors to clusters and identify if they belong.
    """

    def __init__(self, registry, k: int):
        """
        Initialize the Clustering class.

        Args:
            registry (VectorRegistry): The VectorRegistry instance containing vectors.
            k (int): The divisor for determining number of clusters (n // k).
        """
        self.registry = registry
        self.k = k
        self.model = None
        self.cluster_centers_ = None

    def cluster(self):
        """
        Perform KMeans clustering with n // k clusters.
        Returns:
            KMeans: Trained KMeans model.
        """
        if len(self.registry) == 0:
            raise ValueError("The registry is empty. Add vectors before clustering.")

        n_clusters = max(1, len(self.registry) // self.k)
        data = np.stack(self.registry.vectors)

        self.model = KMeans(n_clusters=n_clusters, random_state=42)
        self.model.fit(data)
        self.cluster_centers_ = self.model.cluster_centers_

        return self.model

    def distance_to_closest_cluster(self, vector: np.ndarray):
        """
        Compute the distance from a given vector to the closest cluster center.

        Args:
            vector (np.ndarray): The vector to evaluate.

        Returns:
            float: The distance to the nearest cluster.
        """
        if self.cluster_centers_ is None:
            raise ValueError("You must run cluster() before computing distances.")

        distances = np.linalg.norm(self.cluster_centers_ - vector, axis=1)
        return np.min(distances)

    def identify(self, vector: np.ndarray) -> bool:
        """
        Identify if the vector belongs to a known cluster.

        Returns True if the distance to the closest cluster
        is less than 0.1 × average distance between cluster centers.

        Args:
            vector (np.ndarray): The vector to evaluate.

        Returns:
            bool: True if the vector is close enough to a cluster, False otherwise.
        """
        if self.cluster_centers_ is None:
            raise ValueError("You must run cluster() before calling identify().")

        # Compute average inter-cluster distance
        if len(self.cluster_centers_) < 2:
            avg_intercluster_dist = 0.0
        else:
            pairwise_dists = cdist(self.cluster_centers_, self.cluster_centers_)
            avg_intercluster_dist = np.mean(pairwise_dists[np.triu_indices_from(pairwise_dists, k=1)])

        dist_to_cluster = self.distance_to_closest_cluster(vector)

        if avg_intercluster_dist == 0:
            return True  # trivial case: only one cluster

        return dist_to_cluster < 0.1 * avg_intercluster_dist
