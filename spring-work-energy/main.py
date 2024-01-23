import os
from typing import Tuple, List

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import trapz

MASS_OF_CART = 0.255
FILE_PATH = "spring-work-energy/data/"


def plot_force_position(run_data, col_names, run_number, phase):
    plt.plot(run_data[col_names['position']], run_data[col_names['force']], label=f'Run {run_number}')
    plt.fill_between(run_data[col_names['position']], run_data[col_names['force']], alpha=0.2)
    plt.xlabel('Position (m)')
    plt.ylabel('Force (N)')
    plt.title(f'Force vs. Position ({phase}) for Run {run_number}')
    plt.grid(True)
    plt.legend()


def get_column_names(data, run_number):
    return {
        'time': next((col for col in data.columns if 'Time (s)' in col and f'Run {run_number}' in col), None),
        'position': next((col for col in data.columns if 'Position' in col and f'Run {run_number}' in col), None),
        'force': next((col for col in data.columns if 'Force' in col and f'Run {run_number}' in col), None),
        'velocity': next((col for col in data.columns if 'Velocity' in col and f'Run {run_number}' in col), None)
    }


def calculate_area(run_data: pd.DataFrame, col_names) -> float:
    return trapz(run_data[col_names['force']], run_data[col_names['position']])


def split_run(run_data: pd.DataFrame, col_names: dict, mp_time: float) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Process a single run of data by finding the minimum position and fitting a line to the last few points before
    :param mp_time:
    :param run_data:
    :param col_names:
    :return:
    """

    run_data_pre = run_data[run_data[col_names['time']] < mp_time]
    run_data_post = run_data[(run_data[col_names['time']] >= mp_time)]
    return run_data_pre, run_data_post


def process_data(data: pd.DataFrame, col_names: dict) -> pd.DataFrame:
    # Find the index of the first negative force value
    data = data.dropna(subset=[col_names['force']])
    first_negative_force_index = data[
        (data[col_names['force']] < -0.05) | (data[col_names['position']] > 0.05)].index.min()

    # If there is a negative force, truncate the data up to that point
    if pd.notnull(first_negative_force_index):
        data = data.loc[:first_negative_force_index - 1]
    else:
        # If there are no negative forces, use the data as is
        return data

    # Fit a polynomial of degree 1 (line) to the last few points before the artifact
    # Adjust the slice to fit the last few positive points before hitting the hand
    fit_slice = data[data[col_names['force']] >= 0].tail(3)
    coeffs = np.polyfit(fit_slice[col_names['position']], fit_slice[col_names['force']], 1)

    p = np.poly1d(coeffs)
    force_at_zero = p(0)
    if force_at_zero < 0:
        # Add a point where p(x) = 0
        new_point = pd.DataFrame({col_names['position']: [-coeffs[1] / coeffs[0]], col_names['force']: [0]})

    else:
        # Add a point at zero if there isn't a point near or above zero already
        if data[col_names['position']][(data[col_names['position']] >= 0)].isnull().all():
            new_point = pd.DataFrame({col_names['position']: [0], col_names['force']: [force_at_zero]})
        else:
            return data
    data = pd.concat([data, new_point], ignore_index=True).sort_values(
        by=col_names['position'])
    return data


def fit_line(data: pd.DataFrame, col_names: dict, side: str = "head", points: int = 10) -> Tuple[np.poly1d, np.ndarray]:
    """
    Fit a line to the data
    :param data:
    :param col_names:
    :param side: whether to fit the line to the head or tail of the data
    :param points: how many points to use in the fit
    :return:
    """
    data = data[data[col_names['force']] >= 0]

    fit_slice = data[data[col_names['force']] >= 0].head(points * 35) if side == "head" \
        else (data[data[col_names['force']] >= 0] if side == "all"
              else data[data[col_names['force']] >= 0].tail(points))
    coeffs = np.polyfit(fit_slice[col_names['position']], fit_slice[col_names['force']], 1)
    p = np.poly1d(coeffs)
    return p, coeffs

def plot_fit_line_and_annotations(data, col_names, run_number, side='default', color='blue', linestyle='-'):
    # Fit line
    poly, coeffs = fit_line(data, col_names, side)
    plt.plot(data[col_names['position']], poly(data[col_names['position']]), label=f'Fit Line (Run {run_number})',
             color=color, linestyle=linestyle)

    # Calculate area if side is 'default', otherwise it's not needed
    if side == 'default':
        area = calculate_area(data, col_names)
        plt.text(0.95 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0], 0.9 * plt.ylim()[1],
                 f'Work: {area:.2f} J', fontsize=12, verticalalignment="top", ha="right",
                 bbox=dict(facecolor='white', alpha=0.5))

    # Coefficient k
    plt.text(0.95 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0], 0.8 * plt.ylim()[1],
             f'k = {coeffs[0]:.2f} N/m', fontsize=12, verticalalignment="top", ha="right",
             bbox=dict(facecolor='white', alpha=0.5))


# noinspection PyTypeChecker
def graph(file, num):
    inum = num
    multi_run = file == "spring-work-energy/data/rubberband.csv"

    data = pd.read_csv(file)

    # We want to use two different runs and use them as pre and post data

    run_numbers = sorted(set(col.split(' ')[-1] for col in data.columns if 'Run' in col))
    if multi_run:  # convert this list into a list of tuples
        run_numbers = [(run_numbers[i], run_numbers[i + 1]) for i in range(0, len(run_numbers), 2)]

    for r1 in run_numbers:  # each run could be a individual run or a tuple of two runs
        print(f"Processing Run {num}")
        if multi_run:
            r1, r2 = r1
            run_data_pre = data.filter(regex=f'Run {r1}').copy()
            run_data_post = data.filter(regex=f'Run {r2}').copy()
            col_names_pre = get_column_names(data, r1)
            col_names_post = get_column_names(data, r2)

            # Find the maximum time value in the pre-run data, as well as the position at that time
            max_time_pre = run_data_pre[col_names_pre['time']].max()
            pos_at_max_time_pre = run_data_pre.loc[
                run_data_pre[col_names_pre['time']].idxmax(), col_names_pre['position']]

            run_data_post[col_names_post['time']] += max_time_pre
            run_data_post[col_names_post['position']] += pos_at_max_time_pre

            # replace all `r2`s in the column with `r1`s
            columns_to_rename = {col: col.replace(f'Run {r2}', f'Run {r1}') for col in run_data_post.columns}
            mod_data = run_data_post.rename(columns=columns_to_rename)

            # Concatenate pre and post data
            run_data = (pd.concat([run_data_pre, mod_data], ignore_index=True)
                        .filter(regex=f'Run {r1}')
                        .copy()
                        .dropna(subset=col_names_pre.values()))
            run_data_pre.dropna(subset=col_names_pre.values())

            col_names = col_names_pre

            run_data_pre = run_data_pre.dropna(subset=col_names_pre.values())
            run_data_post = process_data(run_data_post, col_names_post)
        else:
            run_data = data.filter(regex=f'Run {r1}').copy()
            col_names = get_column_names(data, r1)
            # we need to initialize these variables to avoid a NameError- col_names should not be used anywhere else
            col_names_pre = get_column_names(data, r1)
            col_names_post = get_column_names(data, r1)
            min_pos_index = run_data[col_names['position']].idxmin()
            mp_time = run_data.loc[min_pos_index, col_names['time']]
            run_data_pre, run_data_post = split_run(run_data, col_names, mp_time)
            run_data_post = process_data(run_data_post, col_names)

        # Drop NaN values
        run_data = run_data.dropna(subset=col_names.values())

        plt.figure(figsize=(12, 16))

        plt.subplot(3, 2, 1)
        plot_force_position(run_data_pre, col_names_pre, num, 'Pull Back')

        # fit line for the pre data
        poly, coeffs = fit_line(run_data_pre, col_names_pre)
        plt.plot(run_data_pre[col_names_pre['position']], poly(run_data_pre[col_names_pre['position']]),
                 label=f'Fit Line (Run {r1})')

        poly, coeffs = fit_line(run_data_pre, col_names_pre, points=5)
        plt.plot(run_data_pre[col_names_pre['position']], poly(run_data_pre[col_names_pre['position']]),
                 label=f'Fit Line (Run {r1})',
                 color='blue', linestyle='--')

        area_pre = calculate_area(run_data_pre, col_names_pre)
        plt.text(0.95 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0], 0.9 * plt.ylim()[1],
                 f'Work of Elongation: {area_pre:.2f} J',
                 fontsize=12, verticalalignment="top", ha="right", bbox=dict(facecolor='white', alpha=0.5))
        plt.text(0.95 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0], 0.8 * plt.ylim()[1],
                 f'k = {coeffs[0]:.2f} N/m',
                 fontsize=12, verticalalignment="top", ha="right", bbox=dict(facecolor='white', alpha=0.5))

        plt.subplot(3, 2, 2)
        plot_force_position(run_data_post, col_names_post, num, 'Release')

        # fit line for post data
        poly, coeffs = fit_line(run_data_post, col_names_post, side="tail")
        positive_poly_values = poly(run_data_post[col_names_post['position']])
        positive_poly_values[positive_poly_values < 0] = np.nan
        plt.plot(run_data_post[col_names_post['position']], positive_poly_values, label=f'Fit Line (Run {r1})')

        area_post = calculate_area(run_data_post, col_names_post)
        plt.text(0.95 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0], 0.9 * plt.ylim()[1],
                 f'Work of Release: {area_post:.2f} J',
                 fontsize=12, verticalalignment='top', ha="right", bbox=dict(facecolor='white', alpha=0.5))
        plt.text(0.95 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0], 0.8 * plt.ylim()[1],
                 f'k = {coeffs[0]:.2f} N/m',
                 fontsize=12, verticalalignment="top", ha="right", bbox=dict(facecolor='white', alpha=0.5))

        plt.subplot(3, 2, 3)
        plt.plot(run_data[col_names['position']], run_data[col_names['velocity']], label=f'Run {num}')
        plt.xlabel('Position (m)')
        plt.ylabel('Velocity (m/s)')
        plt.title(f'Velocity vs. Position for Run {num}')
        plt.grid(True)
        plt.legend()

        max_v = max(run_data[col_names['velocity']])
        max_KE = 0.5 * MASS_OF_CART * max_v ** 2
        plt.text(0.95 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0],
                 0.8 * (plt.ylim()[1] - plt.xlim()[0]) + plt.xlim()[0],
                 f'Max Velocity: {max_v:.2f} m/s\nMax KE: {max_KE:.2f} J',
                 fontsize=12, horizontalalignment='right', bbox=dict(facecolor='white', alpha=0.5))

        plt.subplot(3, 2, 4)
        plt.plot(run_data[col_names['time']], run_data[col_names['position']], label=f'Run {num}')
        plt.xlabel('Time (s)')
        plt.ylabel('Position (m)')
        plt.title(f'Position vs. Time for Run {num}')
        plt.grid(True)
        plt.legend()

        # Find the time at which the position is minimum
        min_pos_index = run_data[col_names['position']].idxmin()
        mp_time = run_data.loc[min_pos_index, col_names['time']]
        plt.text(0.05 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0],
                 0.85 * (plt.ylim()[1] - plt.xlim()[0]) + plt.xlim()[0],
                 f'Time of Minimum Position: {mp_time:.2f}s', fontsize=12, ha="left",
                 bbox=dict(facecolor='white', alpha=0.5))

        # Additional subplot for the overlay graph
        plt.subplot(3, 2, (5, 6))  # This spans the fifth and sixth positions

        # Plot the retracting and release data
        plt.plot(run_data_pre[col_names_pre['position']], run_data_pre[col_names_pre['force']],
                 label=f'Retracting (Run {num})', color='red')
        plt.fill_between(run_data_pre[col_names_pre['position']], 0, run_data_pre[col_names_pre['force']], color='red',
                         alpha=0.2)
        plt.plot(run_data_post[col_names_post['position']], run_data_post[col_names_post['force']],
                 label=f'Release (Run {num})', color='blue')
        plt.fill_between(run_data_post[col_names_post['position']], 0, run_data_post[col_names_post['force']],
                         color='blue',
                         alpha=0.2)

        plt.xlabel('Position (m)')
        plt.ylabel('Force (N)')
        plt.title(f'Overlay of Retracting and Release for Run {num}')
        plt.grid(True)
        plt.legend()

        # find area between the runs by subtracting
        area_hysteresis = area_pre + area_post
        plt.text(0.95 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0], 0.8 * plt.ylim()[1],
                 f'Hysteresis Area: {area_hysteresis:.2f} J',
                 fontsize=12, verticalalignment="top", ha="right", bbox=dict(facecolor='white', alpha=0.5))

        # credit text at bottom of figure
        plt.figtext(0.02, 0.01, "Source Code Available at github.com/ZenoCoding/AP-Physics-1/", fontsize=8)
        plt.figtext(0.98, 0.01, 'Plotted by Tycho Young using matplotlib', ha='right', va='bottom', fontsize=8)

        plt.tight_layout()
        plt.show()
        num += 1
    return num - inum


def main():
    # loop through all files in the data folder
    count = 1
    for file in os.listdir(FILE_PATH):
        if file.endswith(".csv"):
            print(f"Processing {file}")
            count += graph(FILE_PATH + file, count)


if __name__ == "__main__":
    main()
