import json
import click
import numpy as np


def earth_distance(coords1, coords2):
    # Radius of the Earth in kilometers
    R = 6371.0

    # Unpack the coordinates
    lat1, lon1 = coords1
    lat2, lon2 = coords2

    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = np.radians([lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    # Distance in kilometers
    distance = R * c
    return distance


def evaluate_geolocation(coords_gt, coords_hat):
    """
    Compute the FP, FN and median distance between the ground truth coordinates and the predicted coordinates
    :param coords_gt: list of ground truth coordinates.
    :param coords_hat: list of predicted coordinates.
    """

    if len(coords_gt) == 0 and len(coords_hat) == 0:
            return 0, 0, np.nan

    # Compute distance matrix between two points on Earth
    distance_matrix = np.array([[earth_distance(gt, coords) for coords in coords_hat] for gt in coords_gt])

    # Naive association
    n_match = 0
    distances = []

    while distance_matrix.size > 0 and np.min(distance_matrix) < np.inf:
        min_idx = np.unravel_index(np.argmin(distance_matrix, axis=None), distance_matrix.shape)
        distances.append(distance_matrix[min_idx])
        n_match += 1
        
        distance_matrix[min_idx[0], :] = np.inf
        distance_matrix[:, min_idx[1]] = np.inf

    # Compute FP and FN
    fp = len(coords_hat) - n_match
    fn = len(coords_gt) - n_match

    # Compute average distance for matched pairs
    med_distance = np.median(distances) if distances else np.nan

    return fp, fn, med_distance


@click.command()
@click.option('--method', required=True, type=str, help="Name of the Gemini model")
def main(method):

    # Open data
    with open(f"./results/{method}.json", encoding='utf-8') as file:
        messages = json.load(file)

    list_fp, list_fn, list_med_distance = [], [], []
    for message in messages:

        fp, fn, med_distance = evaluate_geolocation(coords_gt=message['coordinates_gt'], coords_hat=message['coordinates'])

        list_fp.append(fp)
        list_fn.append(fn)
        list_med_distance.append(med_distance)

    print(f"Number of FP with the baseline model: {sum(list_fp)}")
    print(f"Number of FN with the baseline model: {sum(list_fn)}")
    print(f"Mean median distance with the baseline model: {np.nanmean(list_med_distance):0.1f} km")


if __name__ == '__main__':
    main()