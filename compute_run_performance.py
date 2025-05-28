import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def extract_agent_type(jsonl_path):
    """
    Extract the agent type from a debug_gym.jsonl file.
    
    Args:
        jsonl_path (str): Path to the debug_gym.jsonl file
        
    Returns:
        str: The agent type or "Unknown" if not found
    """
    try:
        with open(jsonl_path, 'r') as f:
            data = json.loads(f.read())
            # Extract agent type if available
            if "config" in data and "agent_type" in data["config"]:
                return data["config"]["agent_type"]
            return "Unknown"
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {jsonl_path}: {e}")
        return "Unknown"

def analyze_tasks_in_run(run_dir):
    """
    Analyze all tasks within a specific run directory.
    
    Args:
        run_dir (str): Path to the run directory
        
    Returns:
        tuple: Tuple containing (successful_tasks, total_tasks, agent_type)
    """
    successful_tasks = []
    total_valid_tasks = []
    agent_type = "Unknown"
    agent_type_extracted = False
    
    # Check if this is a run directory containing tasks
    has_tasks = False
    for item in os.listdir(run_dir):
        item_path = os.path.join(run_dir, item)
        if os.path.isdir(item_path):
            for root, dirs, files in os.walk(item_path):
                if 'debug_gym.jsonl' in files:
                    has_tasks = True
                    break
            if has_tasks:
                break

    if not has_tasks:
        return successful_tasks, total_valid_tasks, agent_type
    
    # Walk through all directories and files in this run
    for root, dirs, files in os.walk(run_dir):
        # Check if debug_gym.jsonl exists in this directory
        if 'debug_gym.jsonl' in files:
            # Count the number of files to determine if the task ran correctly
            task_files_count = len([f for f in files if os.path.isfile(os.path.join(root, f))])
            
            if task_files_count < 3:
                continue  # Skip tasks that don't have at least 3 files
            
            jsonl_path = os.path.join(root, 'debug_gym.jsonl')
            
            # Extract agent type if we haven't already
            if not agent_type_extracted:
                agent_type = extract_agent_type(jsonl_path)
                agent_type_extracted = True
            
            try:
                with open(jsonl_path, 'r') as f:
                    # Read the content of the file
                    data = json.loads(f.read())
                    
                    # Add to total valid tasks
                    total_valid_tasks.append(root)
                    
                    # Check if the task was successful
                    if data.get('success', False):
                        successful_tasks.append(root)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading {jsonl_path}: {e}")
                continue
    
    return successful_tasks, total_valid_tasks, agent_type

def compute_all_runs_performance(base_dir):
    """
    Compute performance metrics for all runs in the directory structure.
    
    Args:
        base_dir (str): The base directory containing model folders
        
    Returns:
        dict: Dictionary with performance data for each run
    """
    performance_data = {}
    
    # List all model folders
    try:
        model_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    except FileNotFoundError:
        print(f"Directory not found: {base_dir}")
        return performance_data
    
    # Process each model folder
    for model_folder in model_folders:
        model_path = os.path.join(base_dir, model_folder)
        
        # Check if this is a model folder with run folders inside
        run_folders = []
        for item in os.listdir(model_path):
            item_path = os.path.join(model_path, item)
            if os.path.isdir(item_path):
                run_folders.append(item)
        
        if not run_folders:
            # This might be a direct run folder
            successful, total, agent_type = analyze_tasks_in_run(model_path)
            if total:  # Only add if there are valid tasks
                performance_data[model_folder] = {
                    "successful": len(successful),
                    "total": len(total),
                    "agent_type": agent_type
                }
        else:
            # Process each run folder within the model folder
            for run_folder in run_folders:
                run_path = os.path.join(model_path, run_folder)
                successful, total, agent_type = analyze_tasks_in_run(run_path)
                if total:  # Only add if there are valid tasks
                    run_key = f"{model_folder}/{run_folder}"
                    performance_data[run_key] = {
                        "successful": len(successful),
                        "total": len(total),
                        "agent_type": agent_type
                    }
    
    return performance_data

def format_terminal_output(performance_data, base_dir):
    """
    Format the performance data for terminal display.
    
    Args:
        performance_data (dict): The performance data for all runs
        base_dir (str): The base directory that was analyzed
        
    Returns:
        str: Formatted string for terminal output
    """
    try:
        # Get terminal width for better formatting
        terminal_width = os.get_terminal_size().columns
    except (AttributeError, OSError):
        terminal_width = 100  # Default width if can't determine
    
    separator = "=" * terminal_width
    
    # Group runs by model for better organization
    model_groups = defaultdict(list)
    for run_key, data in performance_data.items():
        if "/" in run_key:
            model_name = run_key.split("/")[0]
            run_id = run_key.split("/")[1]
            model_groups[model_name].append((run_id, data))
        else:
            # This is a direct run without nested folders
            model_groups[run_key].append(("", data))
    
    # Prepare the output
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = [
        separator,
        f"RUN PERFORMANCE REPORT - {os.path.basename(base_dir)} (Generated at {timestamp})".center(terminal_width),
        separator,
    ]
    
    # Add header for the table
    output.append(f"{'Model/Run':<50} {'Agent Type':<25} {'Tasks':<10} {'Success':<10} {'Rate':<10}")
    output.append("-" * terminal_width)
    
    # Track overall statistics
    total_tasks = 0
    total_success = 0
    
    # Define the desired agent order
    agent_order = ["rewrite_agent", "debug_agent", "debug_5_agent"]
    
    # Add data for each model and its runs
    for model_name in sorted(model_groups.keys()):
        runs = model_groups[model_name]
        
        # Sort runs by agent type according to the defined order
        def sort_key(run_item):
            agent_type = run_item[1]['agent_type']
            if agent_type in agent_order:
                return agent_order.index(agent_type)
            return len(agent_order) # Place unknown agent types at the end

        sorted_runs = sorted(runs, key=sort_key)
        
        # If there are multiple runs for this model, add a model header
        if len(sorted_runs) > 1 or (len(sorted_runs) == 1 and sorted_runs[0][0]): # also show model header if it's a single named run
            output.append(f"\nModel: {model_name}")
        
        # Add each run's data
        for run_id, data in sorted_runs: # Iterate over sorted_runs
            # Calculate success rate
            success_rate = (data["successful"] / data["total"]) * 100 if data["total"] > 0 else 0
            
            # Update overall statistics
            total_tasks += data["total"]
            total_success += data["successful"]
            
            # Format the display name based on whether there are multiple runs
            if (len(sorted_runs) > 1 or (len(sorted_runs) == 1 and run_id)) and run_id:
                display_name = f"  {run_id}"  # Indent run IDs under a model
            else:
                display_name = model_name  # Just show the model name for single runs or when run_id is empty
            
            # Add formatted row
            output.append(
                f"{display_name:<50} {data['agent_type']:<25} {data['total']:<10} "
                f"{data['successful']:<10} {success_rate:.2f}%"
            )
    
    # Add overall statistics
    overall_rate = (total_success / total_tasks) * 100 if total_tasks > 0 else 0
    output.append(separator)
    output.append(f"OVERALL PERFORMANCE: {total_success}/{total_tasks} tasks successful ({overall_rate:.2f}%)".center(terminal_width))
    output.append(separator)
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description='Compute performance metrics for each run in a directory.')
    parser.add_argument('directory', type=str, help='Directory containing model and run folders')
    parser.add_argument('--output', '-o', type=str, help='Output file for the report', default=None)
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    args = parser.parse_args()
    
    base_dir = args.directory
    
    # Compute performance for all runs
    performance_data = compute_all_runs_performance(base_dir)
    
    if not performance_data:
        print(f"No valid runs found in {base_dir}")
        return
    
    # Format output for terminal display
    formatted_output = format_terminal_output(performance_data, base_dir)
    
    # Try to use colored output if possible
    if not args.no_color:
        try:
            import colorama
            from colorama import Fore, Style
            colorama.init()
            
            lines = formatted_output.split("\n")
            for i, line in enumerate(lines):
                # Color the header and separator lines
                if "=" in line and len(line) > 30:
                    print(Fore.CYAN + line + Style.RESET_ALL)
                # Color the column headers
                elif "Model/Run" in line and "Agent Type" in line:
                    print(Fore.GREEN + Style.BRIGHT + line + Style.RESET_ALL)
                # Color model headers
                elif line.startswith("\nModel: "):
                    print(Fore.BLUE + Style.BRIGHT + line + Style.RESET_ALL)
                # Color the data rows based on success rate
                elif "%" in line and not "OVERALL PERFORMANCE" in line:
                    try:
                        rate = float(line.split("%")[0].split()[-1])
                        if rate >= 70:
                            print(Fore.GREEN + line + Style.RESET_ALL)
                        elif rate >= 40:
                            print(Fore.YELLOW + line + Style.RESET_ALL)
                        else:
                            print(Fore.RED + line + Style.RESET_ALL)
                    except (ValueError, IndexError):
                        print(line)
                # Color the overall performance line
                elif "OVERALL PERFORMANCE" in line:
                    print(Fore.MAGENTA + Style.BRIGHT + line + Style.RESET_ALL)
                else:
                    print(line)
        except ImportError:
            # Fall back to plain output if colorama is not available or disabled
            print(formatted_output)
    else:
        print(formatted_output)
    
    # Write to output file if specified
    if args.output:
        try:
            with open(args.output, 'w') as f:
                f.write(formatted_output)
            print(f"\nReport written to: {args.output}")
        except IOError as e:
            print(f"Error writing to output file: {e}")
    else:
        # Auto-generate a filename
        output_file = os.path.join(base_dir, f"run_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        try:
            with open(output_file, 'w') as f:
                f.write(formatted_output)
            print(f"\nReport written to: {output_file}")
        except IOError as e:
            print(f"Error writing to output file: {e}")

if __name__ == "__main__":
    main()
