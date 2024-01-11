import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import trapz


def plot_force_position(run_data, col_names, run_number, phase):
    plt.plot(run_data[col_names['position']], run_data[col_names['force']], label=f'Run {run_number}')
    plt.fill_between(run_data[col_names['position']], run_data[col_names['force']], alpha=0.2)
    plt.xlabel('Position (m)')
    plt.ylabel('Force (N)')
    plt.title(f'Force vs. Position ({phase}) for Run {run_number}')
    plt.grid(True)
    plt.legend()


def calculate_area(run_data, col_names):
    return trapz(run_data[col_names['force']], run_data[col_names['position']])


def main():
    MASS_OF_CART = 0.255
    file_path = "data/rubberband.csv"
    data = pd.read_csv(file_path)

    run_numbers = sorted(set(col.split(' ')[-1] for col in data.columns if 'Run' in col))

    for run_number in run_numbers:
        run_data = data.filter(regex=f'Run {run_number}')
        col_names = {
            'time': next((col for col in run_data.columns if 'Time (s)' in col), None),
            'position': next((col for col in run_data.columns if 'Position' in col), None),
            'force': next((col for col in run_data.columns if 'Force' in col), None),
            'velocity': next((col for col in run_data.columns if 'Velocity' in col), None)
        }

        if not all(col_names.values()):
            print(f"Missing data for Run {run_number}: Position, Force, or Velocity data not found.")
            continue

        # Drop NaN values and get post-mp_time data
        run_data = run_data.dropna(subset=col_names.values())
        min_pos_index = run_data[col_names['position']].idxmin()
        mp_time = run_data.loc[min_pos_index, col_names['time']]

        run_data_pre = run_data[run_data[col_names['time']] < mp_time]
        run_data_post_mp_time = run_data[(run_data[col_names['time']] >= mp_time)]

        # Find the index of the first negative force value
        first_negative_force_index = run_data_post_mp_time[run_data_post_mp_time[col_names['force']] < 0].index.min()

        # If there is a negative force, truncate the data up to that point
        if pd.notnull(first_negative_force_index):
            run_data_post = run_data_post_mp_time.loc[:first_negative_force_index - 1]
        else:
            # If there are no negative forces, use the data as is
            run_data_post = run_data_post_mp_time

        # Fit a polynomial of degree 1 (line) to the last few points before the artifact
        # Adjust the slice to fit the last few positive points before hitting the hand
        fit_slice = run_data_post[run_data_post[col_names['force']] >= 0].tail(5)  # Example: last 5 points
        coeffs = np.polyfit(fit_slice[col_names['position']], fit_slice[col_names['force']], 1)

        # Create a polynomial from the coefficients
        p = np.poly1d(coeffs)

        # Use the fitted polynomial to estimate the force at x=0
        force_at_zero = p(0)

        # Append this estimated point at x=0 to your post data, if it does not already exist
        if 0 not in run_data_post[col_names['position']].values:
            new_point = pd.DataFrame({col_names['position']: [0], col_names['force']: [force_at_zero]})
            run_data_post = pd.concat([run_data_post, new_point], ignore_index=True).sort_values(
                by=col_names['position'])

        plt.figure(figsize=(12, 16))

        plt.subplot(3, 2, 1)
        plot_force_position(run_data_pre, col_names, run_number, 'Pull Back')
        area_pre = calculate_area(run_data_pre, col_names)
        plt.text(0.95 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0], 0.9 * plt.ylim()[1],
                 f'Work of Elongation: {area_pre:.2f} J',
                 fontsize=12, verticalalignment="top", ha="right", bbox=dict(facecolor='white', alpha=0.5))

        plt.subplot(3, 2, 2)
        plot_force_position(run_data_post, col_names, run_number, 'Release')
        area_post = calculate_area(run_data_post, col_names)
        plt.text(0.95 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0], 0.9 * plt.ylim()[1],
                 f'Work of Release: {area_post:.2f} J',
                 fontsize=12, verticalalignment='top', ha="right", bbox=dict(facecolor='white', alpha=0.5))

        plt.subplot(3, 2, 3)
        plt.plot(run_data[col_names['position']], run_data[col_names['velocity']], label=f'Run {run_number}')
        plt.xlabel('Position (m)')
        plt.ylabel('Velocity (m/s)')
        plt.title(f'Velocity vs. Position for Run {run_number}')
        plt.grid(True)
        plt.legend()

        max_v = max(run_data[col_names['velocity']])
        max_KE = 0.5 * MASS_OF_CART * max_v ** 2
        plt.text(0.95 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0],
                 0.8 * (plt.ylim()[1] - plt.xlim()[0]) + plt.xlim()[0],
                 f'Max Velocity: {max_v:.2f} m/s\nMax KE: {max_KE:.2f} J',
                 fontsize=12, horizontalalignment='right', bbox=dict(facecolor='white', alpha=0.5))

        plt.subplot(3, 2, 4)
        plt.plot(run_data[col_names['time']], run_data[col_names['position']], label=f'Run {run_number}')
        plt.xlabel('Time (s)')
        plt.ylabel('Position (m)')
        plt.title(f'Position vs. Time for Run {run_number}')
        plt.grid(True)
        plt.legend()
        plt.text(0.05 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0],
                 0.85 * (plt.ylim()[1] - plt.xlim()[0]) + plt.xlim()[0],
                 f'Time of Minimum Position: {mp_time:.2f}s', fontsize=12, ha="left",
                 bbox=dict(facecolor='white', alpha=0.5))

        # Additional subplot for the overlay graph
        plt.subplot(3, 2, (5, 6))  # This spans the fifth and sixth positions

        # Plot the retracting and release data
        plt.plot(run_data_pre[col_names['position']], run_data_pre[col_names['force']],
                 label=f'Retracting (Run {run_number})', color='red')
        plt.fill_between(run_data_pre[col_names['position']], 0, run_data_pre[col_names['force']], color='red',
                         alpha=0.2)
        plt.plot(run_data_post[col_names['position']], run_data_post[col_names['force']],
                 label=f'Release (Run {run_number})', color='blue')
        plt.fill_between(run_data_post[col_names['position']], 0, run_data_post[col_names['force']], color='blue',
                         alpha=0.2)

        plt.xlabel('Position (m)')
        plt.ylabel('Force (N)')
        plt.title(f'Overlay of Retracting and Release for Run {run_number}')
        plt.grid(True)
        plt.legend()

        # find area between the runs by subtracting
        area_hysteresis = area_pre + area_post
        plt.text(0.95 * (plt.xlim()[1] - plt.xlim()[0]) + plt.xlim()[0], 0.8 * plt.ylim()[1],
                 f'Hysteresis Area: {area_hysteresis:.2f} J',
                 fontsize=12, verticalalignment="top", ha="right", bbox=dict(facecolor='white', alpha=0.5))

        # Add small text at the bottom of the figure
        plt.figtext(0.98, 0.01, 'Plotted by Tycho Young using matplotlib', ha='right', va='bottom', fontsize=8)

        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    main()
