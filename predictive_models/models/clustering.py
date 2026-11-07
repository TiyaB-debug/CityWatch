"""Group Manhattan cells by their historical collision and complaint profiles."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


def cluster(cells):
    features = ["Vehicle collisions", "Cyclist injury collisions", "DOT complaints"]
    scaled = StandardScaler().fit_transform(np.log1p(cells[features]))
    options = {}
    for k in range(2, 7):
        model = KMeans(n_clusters=k, n_init=20, random_state=42).fit(scaled)
        options[k] = (float(silhouette_score(scaled, model.labels_)), model)
    selected = max(options, key=lambda k: options[k][0])
    labels = options[selected][1].labels_
    # Give cluster labels a stable order by their average injury collision count.
    injuries = cells["Cyclist injury collisions"].groupby(labels).mean().sort_values()
    order = {label: rank for rank, label in enumerate(injuries.index, start=1)}
    assigned = cells.assign(cluster=[order[label] for label in labels])
    profiles = pd.DataFrame(scaled, columns=features).assign(cluster=assigned.cluster.to_numpy())
    return assigned, profiles.groupby("cluster").mean(), {
        "k": selected, "silhouette": {k: score for k, (score, _) in options.items()},
        "cluster_sizes": assigned.cluster.value_counts().sort_index().to_dict(),
    }
