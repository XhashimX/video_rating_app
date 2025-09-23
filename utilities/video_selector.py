from flask import flash, render_template, request, redirect, url_for, session
from utilities.data_manager import load_data, save_data
from utilities.elo_calculator import update_ratings_multiple
import json
import random
import traceback # Import traceback for detailed error logging

def _select_unique_by_name(candidates, k):
    """
    candidates: قائمة tuples على شكل (video_id, info_dict)
    k: عدد الفيديوهات المرغوب اختيارها
    """
    import random
    sel, seen = [], set()
    pool = candidates[:]
    random.shuffle(pool)
    print("DEBUG [_select_unique_by_name] pool after shuffle:",
          [(vid, info.get('names'), info.get('name')) for vid, info in pool])
    # نختار أولاً فيديوهات بأسماء مختلفة
    for vid, info in pool:
        nm = info.get('names') or info.get('name')
        print(f"DEBUG [select loop] considering vid={vid}, nm={nm!r}, seen_before={seen}")
        if nm not in seen:
            sel.append((vid, info))
            seen.add(nm)
        if len(sel) == k:
            break
    print("DEBUG [after select unique] sel:",
          [(v, info.get('names') or info.get('name')) for v, info in sel])
    # إذا لم نصل للعدد المطلوب، نملأ الباقي بأي فيديو متاح
    if len(sel) < k:
        print("DEBUG [fallback] need", k, "got", len(sel),
              "remaining pool:", [(v, i.get('names'), i.get('name')) for v, i in candidates if (v, i) not in sel])
        remaining = [item for item in candidates if item not in sel]
        sel += random.sample(remaining, min(len(remaining), k - len(sel)))
    return sel

# Renamed function to avoid naming conflicts
def choose_videos_function(data, mode, value=None, num_videos=2, use_dynamic_weighting=False,
                  competition_type='random', specific_videos=[], session=None):
    """
    Selects videos based on the given mode, with optional dynamic weighting.
    Includes detailed logging for debugging.
    """
    print(f"\n--- Entering choose_videos_function ---") # DEBUG
    print(f"Parameters: mode={mode}, value={value}, num_videos={num_videos}, dynamic_weighting={use_dynamic_weighting}, comp_type={competition_type}, specific_videos={specific_videos}") # DEBUG

    if not data:
        print("ERROR: choose_videos called with empty data.") # DEBUG
        return []

    videos = list(data.items())
    print(f"Total videos loaded: {len(videos)}") # DEBUG
    filtered_videos = []

    try: # Wrap filtering logic in try-except for better error handling
        if specific_videos:
            print(f"Filtering based on specific videos: {specific_videos}") # DEBUG
            # Ensure specified videos actually exist in data
            filtered_videos = [(k, v) for k, v in videos if k in specific_videos]
            # Check if we found all specified videos
            found_specific_count = len(filtered_videos)
            if found_specific_count != len(specific_videos):
                missing = [v for v in specific_videos if v not in data]
                print(f"WARNING: {len(missing)} specified videos not found in data: {missing}") # DEBUG
            print(f"Videos after specific filter: {len(filtered_videos)}") # DEBUG
        elif mode == 1:  # اختيار فيديوهات عشوائية
            print("Mode 1: Selecting all videos.") # DEBUG
            filtered_videos = videos
        elif mode == 2:  # اختيار أفضل فيديوهات (Note: This mode is usually not used for selection, but for display. Included for completeness)
            print("Mode 2: Sorting by rating (desc).") # DEBUG
            # Filter is still applied based on the mode's intent (though for mode 2, intent is sorting)
            filtered_videos = videos # Mode 2 typically doesn't filter, just provides a sorted list to pick from.
            # If you strictly wanted *only* the top N based on rating, you'd apply [:num_videos] here or later.
            # Let's assume Mode 2 means "select *from* the list sorted by rating". The final random/weighted selection will then pick from this.
            print(f"Videos after mode 2 (no filter): {len(filtered_videos)}") # DEBUG
        elif mode == 3:  # اختيار فيديوهات بتقييم أقل من قيمة معينة
            target_value = float(value) if value is not None and isinstance(value, (int, float)) else float('inf')
            print(f"Mode 3: Filtering rating < {target_value}") # DEBUG
            filtered_videos = [(k, v) for k, v in videos if v.get('rating', 1000) < target_value]
            print(f"Videos after mode 3 filter: {len(filtered_videos)}") # DEBUG
        elif mode == 4:  # اختيار فيديوهات بتقييم أعلى من قيمة معينة
            target_value = float(value) if value is not None and isinstance(value, (int, float)) else 0
            print(f"Mode 4: Filtering rating > {target_value}") # DEBUG
            filtered_videos = [(k, v) for k, v in videos if v.get('rating', 1000) > target_value]
            print(f"Videos after mode 4 filter: {len(filtered_videos)}") # DEBUG
        elif mode == 5:  # اختيار فيديوهات بين رقمين
            print(f"Mode 5: Filtering between values. Input value dict: {value}") # DEBUG
            if isinstance(value, dict) and 'min_value' in value and 'max_value' in value:
                min_val = value.get('min_value')
                max_val = value.get('max_value')
                if isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)):
                    print(f"Mode 5: Applying filter {min_val} <= rating <= {max_val}") # DEBUG
                    filtered_videos = [(k, v) for k, v in videos if min_val <= v.get('rating', 1000) <= max_val]
                    print(f"Videos after mode 5 filter: {len(filtered_videos)}") # DEBUG
                else:
                    print("ERROR Mode 5: min_value or max_value are not valid numbers.") # DEBUG
                    return []
            else:
                print("ERROR Mode 5: Value is not a dictionary or missing keys ('min_value', 'max_value').") # DEBUG
                return []
        elif mode == 6:  # اختيار فيديوهات خارج نطاق قيمتين
            print(f"Mode 6: Filtering outside range. Input value dict: {value}") # DEBUG
            if isinstance(value, dict) and 'min_value' in value and 'max_value' in value:
                min_val = value.get('min_value')
                max_val = value.get('max_value')
                if isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)):
                     print(f"Mode 6: Applying filter rating < {min_val} OR rating > {max_val}") # DEBUG
                     filtered_videos = [(k, v) for k, v in videos if v.get('rating', 1000) < min_val or v.get('rating', 1000) > max_val]
                     print(f"Videos after mode 6 filter: {len(filtered_videos)}") # DEBUG
                else:
                    print("ERROR Mode 6: min_value or max_value are not valid numbers.") # DEBUG
                    return []
            else:
                print("ERROR Mode 6: Value is not a dictionary or missing keys ('min_value', 'max_value').") # DEBUG
                return []
        elif mode == 8:  # اختيار فيديوهات من نطاقين
             print(f"Mode 8: Filtering within two ranges. Input value dict: {value}") # DEBUG
             if isinstance(value, dict) and all(k in value for k in ['min_value1', 'max_value1', 'min_value2', 'max_value2']):
                min1, max1 = value.get('min_value1'), value.get('max_value1')
                min2, max2 = value.get('min_value2'), value.get('max_value2')
                if all(isinstance(v, (int, float)) for v in [min1, max1, min2, max2]):
                    print(f"Mode 8: Applying filter ({min1} <= rating <= {max1}) OR ({min2} <= rating <= {max2})") # DEBUG
                    filtered1 = [(k, v) for k, v in videos if min1 <= v.get('rating', 1000) <= max1]
                    filtered2 = [(k, v) for k, v in videos if min2 <= v.get('rating', 1000) <= max2]
                    # Combine and remove duplicates if a video fits both ranges
                    combined_dict = {k: v for k, v in filtered1 + filtered2}
                    filtered_videos = list(combined_dict.items())
                    print(f"Videos after mode 8 filter (range1={len(filtered1)}, range2={len(filtered2)}, combined unique={len(filtered_videos)}): {len(filtered_videos)}") # DEBUG
                else:
                    print("ERROR Mode 8: One or more range values are not valid numbers.") # DEBUG
                    return []
             else:
                 print("ERROR Mode 8: Value is not a dictionary or missing required keys for ranges.") # DEBUG
                 return []
        # START: إضافة منطق للأوضاع الجديدة 9 و 10 للفلترة
        elif mode == 9:  # اختيار فيديوهات بنطاق مرات الظهور
            print(f"Mode 9: Filtering by times_shown range. Input value dict: {value}") # DEBUG
            if isinstance(value, dict) and 'min_times_shown' in value and 'max_times_shown' in value:
                min_ts = value.get('min_times_shown')
                max_ts = value.get('max_times_shown')
                # Ensure min_ts and max_ts are integers
                if isinstance(min_ts, int) and isinstance(max_ts, int):
                    # Ensure min is not greater than max, swap if necessary
                    if min_ts > max_ts:
                         print(f"Mode 9: min_times_shown ({min_ts}) > max_times_shown ({max_ts}). Swapping.") # DEBUG
                         min_ts, max_ts = max_ts, min_ts

                    print(f"Mode 9: Applying filter {min_ts} <= times_shown <= {max_ts}") # DEBUG
                    filtered_videos = [(k, v) for k, v in videos if min_ts <= v.get('times_shown', 0) <= max_ts]
                    print(f"Videos after mode 9 filter: {len(filtered_videos)}") # DEBUG
                else:
                    print("ERROR Mode 9: min_times_shown or max_times_shown are not valid integers.") # DEBUG
                    return []
            else:
                print("ERROR Mode 9: Value is not a dictionary or missing keys ('min_times_shown', 'max_times_shown').") # DEBUG
                return []
        elif mode == 10: # اختيار فيديوهات بوسوم معينة
            print(f"Mode 10: Filtering by specific tags. Input value dict: {value}") # DEBUG
            if isinstance(value, dict) and 'tags' in value:
                required_tags_str = value.get('tags', '')
                # تنظيف قائمة الوسوم المطلوبة: تحويلها إلى حروف صغيرة، إزالة المسافات، وإزالة الوسوم الفارغة
                required_tags_list = {tag.strip().lower() for tag in required_tags_str.split(',') if tag.strip()}
                print(f"Mode 10: Required tags (cleaned): {required_tags_list}") # DEBUG

                if not required_tags_list: # إذا كانت قائمة الوسوم المطلوبة فارغة بعد التنظيف
                    print("WARNING Mode 10: No valid tags provided after cleaning. Selecting all videos.") # DEBUG
                    filtered_videos = videos # Fallback to selecting all videos if tags are empty
                else:
                    temp_filtered_videos = []
                    for k, v_info in videos:
                        video_tags_str = v_info.get('tags', '')
                        # تنظيف وسوم الفيديو الحالية بنفس الطريقة
                        current_video_tags_set = {tag.strip().lower() for tag in video_tags_str.split(',') if tag.strip()}

                        # التحقق مما إذا كانت *جميع* الوسوم المطلوبة موجودة في وسوم الفيديو الحالية
                        if required_tags_list.issubset(current_video_tags_set):
                            temp_filtered_videos.append((k, v_info))
                    filtered_videos = temp_filtered_videos
                    print(f"Videos after mode 10 filter: {len(filtered_videos)}") # DEBUG
            else:
                print("ERROR Mode 10: Value is not a dictionary or missing 'tags' key.") # DEBUG
                return []
        # END: إضافة منطق للأوضاع الجديدة 9 و 10
        elif mode == 7:  # عشوائي ثم الأقرب تقييم
            print("Mode 7: Random then closest rating.") # DEBUG
            if not videos:
                print("WARNING Mode 7: No videos available to choose from.") # DEBUG
                return []

            first_video = None # Will store (name, info_dict) tuple
            # Ring mode logic depends on 'session' and 'last_winner'
            if competition_type == 'ring' and session and session.get('last_winner'):
                last_winner_id = session.get('last_winner')
                print(f"Mode 7 (Ring): Found last winner in session: {last_winner_id}") # DEBUG
                # Find the winner's data in the full videos list
                winner_item = next((item for item in videos if item[0] == last_winner_id), None)
                if not winner_item:
                    print(f"WARNING Mode 7 (Ring): Last winner {last_winner_id} not found in current video list. Choosing random.") # DEBUG
                    first_video = random.choice(videos)
                else:
                    print(f"Mode 7 (Ring): Using last winner {winner_item[0]} as first video.") # DEBUG
                    first_video = winner_item
            else:
                if competition_type == 'ring':
                     print("Mode 7 (Ring): No last winner in session. Choosing random first video.") # DEBUG
                else:
                     print("Mode 7 (Not Ring): Choosing random first video.") # DEBUG
                first_video = random.choice(videos)

            # Add the first video to the filtered list
            filtered_videos.append(first_video)
            # Remaining videos are all videos except the first one
            remaining_videos = [v for v in videos if v[0] != first_video[0]]

            if not remaining_videos:
                print("WARNING Mode 7: Only 1 video available after selecting the first one.") # DEBUG
            elif num_videos > 1:
                first_video_rating = first_video[1].get('rating', 1000)
                print(f"Mode 7: Sorting remaining {len(remaining_videos)} videos by rating difference from {first_video[0]} (Rating: {first_video_rating}).") # DEBUG
                sorted_by_rating_diff = sorted(
                    remaining_videos,
                    key=lambda x: abs(x[1].get('rating', 1000) - first_video_rating)
                )
                needed = num_videos - 1
                selected_others = sorted_by_rating_diff[:min(needed, len(sorted_by_rating_diff))]
                print(f"Mode 7: Selected {len(selected_others)} closest videos.") # DEBUG
                filtered_videos.extend(selected_others)

        else:
             print(f"WARNING: Unknown mode '{mode}' provided.") # DEBUG
             # Default to random if mode is unknown? Or return empty? Returning empty for safety.
             return []

    except Exception as e:
        print(f"ERROR during filtering phase in choose_videos: {e}") # DEBUG
        traceback.print_exc() # Print detailed traceback
        return [] # Return empty on error

    # --- Selection Phase (after filtering) ---
    if not filtered_videos:
        print("WARNING: No videos found after applying mode filters.") # DEBUG
        return []

    print(f"Total videos after filtering phase: {len(filtered_videos)}") # DEBUG
    selected_output = []

    try: # Wrap selection logic in try-except
        if use_dynamic_weighting:
            print("Applying dynamic weighting based on 'times_shown'.") # DEBUG
            # Ensure 'times_shown' exists, default to 0 if not
            for vid, info in filtered_videos:
                 if 'times_shown' not in info:
                      info['times_shown'] = 0

            min_times_shown = min((info.get('times_shown', 0) for _, info in filtered_videos), default=0)
            print(f"Minimum times shown among filtered videos: {min_times_shown}") # DEBUG

            min_shown_videos = [(vid, info) for vid, info in filtered_videos if info.get('times_shown', 0) == min_times_shown]
            print(f"Number of videos with minimum times shown: {len(min_shown_videos)}") # DEBUG

            if not min_shown_videos:
                print("WARNING: Dynamic weighting - No videos found with minimum times_shown. This shouldn't happen if filtered_videos is not empty.") # DEBUG
                # Fallback to random sample from all filtered videos if this unlikely case occurs

                selected_items = _select_unique_by_name(filtered_videos, min(len(filtered_videos), num_videos))

            elif len(min_shown_videos) <= num_videos:
                print(f"Dynamic weighting: Fewer/equal min-shown videos ({len(min_shown_videos)}) than needed ({num_videos}). Selecting all and shuffling.") # DEBUG
                random.shuffle(min_shown_videos)
                selected_items = min_shown_videos[:num_videos] # Ensure we don't exceed num_videos
            else:
                print(f"Dynamic weighting: More min-shown videos ({len(min_shown_videos)}) than needed ({num_videos}). Sampling {num_videos}.") # DEBUG
                selected_items = random.sample(min_shown_videos, num_videos)

        # --- Random Selection (No Dynamic Weighting) or Ring Mode ---
        else:
            print("Applying random selection (or Ring logic without dynamic weighting).") # DEBUG
            # Handle Ring mode specifically if not using dynamic weighting
            if competition_type == 'ring' and session and session.get('last_winner'):
                last_winner_id = session.get('last_winner')
                print(f"Random/Ring: Ring mode active. Last winner: {last_winner_id}") # DEBUG

                winner_item = next((item for item in filtered_videos if item[0] == last_winner_id), None)
                selected_items = []

                if winner_item:
                    print(f"Random/Ring: Found last winner {winner_item[0]} in filtered list. Adding.") # DEBUG
                    selected_items.append(winner_item)
                    # Remove winner from list before selecting others
                    remaining_filtered = [item for item in filtered_videos if item[0] != last_winner_id]
                else:
                    print(f"WARNING Random/Ring: Last winner {last_winner_id} not found in the filtered list for this mode. Choosing random start.") # DEBUG
                    # If winner not found (e.g., doesn't meet mode criteria), just pick randomly
                    remaining_filtered = filtered_videos # Use the full filtered list
                    # selected_items will be filled below

                needed_others = num_videos - len(selected_items) # How many more do we need?

                if needed_others > 0:
                    if not remaining_filtered:
                         print("WARNING Random/Ring: No other videos available to compete with the winner (or to select randomly).") # DEBUG
                    elif len(remaining_filtered) < needed_others:
                         print(f"WARNING Random/Ring: Not enough remaining videos ({len(remaining_filtered)}) to fill {needed_others} slots. Selecting all available.") # DEBUG
                         selected_items.extend(random.sample(remaining_filtered, len(remaining_filtered))) # Sample to shuffle
                    else:
                         print(f"Random/Ring: Selecting {needed_others} random opponents from {len(remaining_filtered)} remaining.") # DEBUG
                         selected_items.extend(random.sample(remaining_filtered, needed_others))
                else:
                     print("Random/Ring: Already have enough videos (just the winner), or num_videos <= 1.") # DEBUG


                # Ensure final list doesn't exceed num_videos, though logic above should handle it
                selected_items = selected_items[:num_videos]
                random.shuffle(selected_items) # Shuffle the final list for presentation order
                print(f"Random/Ring: Final selected count: {len(selected_items)}") # DEBUG

            else: # Standard random selection
                if competition_type == 'ring':
                     print("Random/Ring: Ring mode but no last winner. Proceeding with standard random.") # DEBUG
                print(f"Standard Random: Selecting {min(len(filtered_videos), num_videos)} videos from {len(filtered_videos)} filtered videos.") # DEBUG

                selected_items = _select_unique_by_name(filtered_videos, min(len(filtered_videos), num_videos))


        # --- Format Output ---
        # Ensure all needed info is present in the data dict before formatting
        selected_output = []
        for vid, info in selected_items:
            if vid in data: # Double check video still exists in the main data dict
                 rating = data[vid].get('rating', 1000)
                 times_shown = data[vid].get('times_shown', 0)
                 tags = data[vid].get('tags', '')
                 selected_output.append((vid, rating, times_shown, tags))
            else:
                 print(f"WARNING: Video {vid} selected but not found in main data dictionary during output formatting.") # DEBUG

    except Exception as e:
         print(f"ERROR during selection phase in choose_videos: {e}") # DEBUG
         traceback.print_exc() # Print detailed traceback
         return [] # Return empty on error


    print(f"--- Exiting choose_videos_function: Returning {len(selected_output)} videos. ---") # DEBUG
    # Ensure we always return a list
    return selected_output if selected_output else []

def select_winner():
    print(f"\n--- Entering select_winner POST route ---") # DEBUG
    print(f"Request.form: {request.form}") # DEBUG

    if not session.get('selected_folder'):
        flash("Please select a folder first.", "warning")
        print("ERROR: No folder selected in session.") # DEBUG
        return redirect(url_for('select_folder'))


    if request.form.get('skip_competition') == 'true':
        print("Action: Skip competition.") # DEBUG
        return skip_competition()

    # --- Process regular competition results ---
    print("Action: Processing competition results.") # DEBUG
    try: # Wrap main logic in try-except
        # Reload competition parameters from the form hidden fields (sent from select_winner.html)
        # These represent the parameters of the competition *just completed*
        mode = request.form.get('mode', type=int)
        num_videos = request.form.get('num_videos', type=int)
        ranking_type = request.form.get('ranking_type')
        competition_type = request.form.get('competition_type') # Get type of completed competition
        value = None # Reconstruct value based on mode

        # Reconstruct 'value' based on hidden fields specific to the mode used
        if mode == 8:
            value = {
                'min_value1': request.form.get('min_value1', type=float), 'max_value1': request.form.get('max_value1', type=float),
                'min_value2': request.form.get('min_value2', type=float), 'max_value2': request.form.get('max_value2', type=float)
            }
        elif mode in [5, 6]:
            value = {'min_value': request.form.get('min_value', type=float), 'max_value': request.form.get('max_value', type=float)}
        elif mode in [3, 4]:
             val_str = request.form.get('value')
             value = float(val_str) if val_str else None # Handle case where value might be empty
        elif mode == 9: # Add reconstruction for mode 9's value
            value = {
                'min_times_shown': request.form.get('min_times_shown', type=int),
                'max_times_shown': request.form.get('max_times_shown', type=int)
            }
        elif mode == 10: # Add reconstruction for mode 10's value
            value = {
                'tags': request.form.get('tags', type=str)
            }

        print(f"Parameters from completed competition form: Mode={mode}, NumVids={num_videos}, RankType={ranking_type}, CompType={competition_type}, Value={value}") # DEBUG

        competition_videos = request.form.getlist('videos') # Videos that participated
        ranks = []
        winner_vid = None # Explicitly track the winner

        print(f"Videos submitted: {competition_videos}") # DEBUG

        if not competition_videos:
             flash("No videos were submitted in the form.", "danger")
             print("ERROR: Form submitted without any 'videos' values.") # DEBUG
             return redirect(url_for('competition'))

        if ranking_type == 'winner_only':
            winner_vid = request.form.get('winner') # Get the winner
            print(f"Winner Only mode. Winner selected: {winner_vid}") # DEBUG
            if not winner_vid:
                flash("Please select a winner.", "danger")
                print("ERROR: Winner_only mode, but no winner selected in form.") # DEBUG
                # It's better to show the same page again if possible, but redirecting for now
                # This might require passing the state back to render_template, complex
                return redirect(url_for('competition'))
            if winner_vid not in competition_videos:
                 flash("Selected winner was not part of the competition videos.", "danger")
                 print(f"ERROR: Submitted winner '{winner_vid}' not in submitted video list: {competition_videos}") # DEBUG
                 return redirect(url_for('competition'))

            # Assign ranks: 1 for winner, 2 for others
            ranks = [1 if vid == winner_vid else 2 for vid in competition_videos]
            print(f"Assigned ranks for winner_only: {ranks}") # DEBUG

        else: # Rank mode
             print("Rank mode. Reading ranks...") # DEBUG
             submitted_ranks = {}
             for i in range(len(competition_videos)):
                 # Ranks might be associated with video ID directly in future form designs
                 # For now, assuming rank_1, rank_2 etc correspond to video order
                 rank_val = request.form.get(f'rank_{i+1}', type=int) # Get rank_1, rank_2 etc.
                 if rank_val is not None:
                      submitted_ranks[competition_videos[i]] = rank_val
                 else:
                     # Handle missing rank - this shouldn't happen with JS validation, but check server-side
                      flash(f"Missing rank for video {i+1}. Please rank all videos.", "danger")
                      print(f"ERROR: Missing rank for video {i+1} ({competition_videos[i]}) in rank mode.") # DEBUG
                      return redirect(url_for('competition')) # Or re-render select_winner

             # Ensure all videos have a rank assigned
             if len(submitted_ranks) != len(competition_videos):
                  flash("Not all videos were ranked.", "danger")
                  print(f"ERROR: Number of ranks ({len(submitted_ranks)}) doesn't match number of videos ({len(competition_videos)}).") # DEBUG
                  return redirect(url_for('competition'))

             # Create the ranks list in the same order as competition_videos
             ranks = [submitted_ranks[vid] for vid in competition_videos]
             print(f"Ranks submitted for rank mode: {ranks}") # DEBUG
             # Determine winner (lowest rank)
             min_rank = min(ranks)
             winners = [vid for vid, r in zip(competition_videos, ranks) if r == min_rank]
             # Handle ties if necessary, for now just take the first one for 'last_winner'
             winner_vid = winners[0] if winners else None
             print(f"Winner(s) in rank mode (rank {min_rank}): {winners}. Using {winner_vid} for session.") # DEBUG


        # --- Load data and apply updates ---
        data = load_data()
        if not data:
            flash("No competition data found.", "danger")
            print("ERROR: Failed to load data before updating ratings.") # DEBUG
            return redirect(url_for('competition'))

        # Prepare data for rating update
        ranked_videos_for_update = []
        for vid, rank in zip(competition_videos, ranks):
            if vid in data:
                # Get current rating, default to 1000 if missing (shouldn't happen ideally)
                current_rating = float(data[vid].get('rating', 1000))
                ranked_videos_for_update.append((vid, current_rating, rank))
            else:
                # This indicates a serious inconsistency
                flash(f"Error: Video {vid} from form not found in loaded data.", "danger")
                print(f"CRITICAL ERROR: Video {vid} submitted in form not found in data.json!") # DEBUG
                return redirect(url_for('competition'))

        # Sort by rank for ELO update function (important!)
        ranked_videos_for_update.sort(key=lambda x: x[2])
        print(f"Data prepared for ELO update: {ranked_videos_for_update}") # DEBUG

        # --- Update Ratings, Win/Loss, Times Shown, Tags ---
        # ELO Update
        update_ratings_multiple(ranked_videos_for_update, data) # Updates data dict in-place
        print("Ratings updated by ELO calculator.") # DEBUG

        # Update win/loss stats and times shown
        for vid in competition_videos:
            if vid in data:
                 # Initialize stats if they don't exist
                 data[vid].setdefault('total_wins', 0)
                 data[vid].setdefault('total_losses', 0)
                 data[vid].setdefault('times_shown', 0)
                 data[vid].setdefault('tags', '') # Ensure tags field exists

                 # Increment win/loss
                 if vid == winner_vid: # Use the determined winner_vid
                     data[vid]['total_wins'] += 1
                 else:
                     data[vid]['total_losses'] += 1

                 # Recalculate win rate
                 total_matches = data[vid]['total_wins'] + data[vid]['total_losses']
                 data[vid]['win_rate'] = (data[vid]['total_wins'] / total_matches) if total_matches > 0 else 0.0

                 # Increment times shown
                 data[vid]['times_shown'] += 1

                 # Update tags - find the corresponding tag input field
                 # Assume tag inputs are named tag_1, tag_2 etc corresponding to video order
                 try:
                      video_index_in_form = competition_videos.index(vid) + 1 # Get 1-based index
                      tags_input = request.form.get(f'tag_{video_index_in_form}', '')
                      # Process tags: split by comma, strip whitespace, remove empty strings
                      processed_tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                      data[vid]['tags'] = ','.join(processed_tags) # Store cleaned tags
                      print(f"Updated tags for {vid}: {data[vid]['tags']}") # DEBUG
                 except (ValueError, IndexError) as e:
                      print(f"WARNING: Could not find or process tags for video {vid} at index {video_index_in_form}. Error: {e}") # DEBUG
                      # Keep existing tags if input not found
            else:
                 # Should not happen due to earlier check, but good to log
                 print(f"WARNING: Video {vid} not found in data during final stat/tag update loop.") # DEBUG


        # Save the updated data
        save_data(data)
        print("Data saved successfully after updates.") # DEBUG
        flash("Ratings, stats, and tags updated successfully!", "success")

        # --- Prepare for Next Competition ---
        # Update last winner in session *if* a winner was determined
        if winner_vid:
            print(f"Updating session 'last_winner': {winner_vid}") # DEBUG
            session['last_winner'] = winner_vid
        else:
             # If no winner (e.g., error during ranking), clear last_winner? Or keep old one?
             # Clearing might be safer if ranking failed.
             session.pop('last_winner', None)
             print("No winner determined for this round, cleared session 'last_winner'.") # DEBUG


        # Determine parameters for the *next* competition
        next_competition_params = None
        if session.get('competitions_queue'):
            print("Competitions queue exists, popping next set of params.") # DEBUG
            # Check if queue is actually empty *before* popping
            if not session['competitions_queue']:
                 print("WARNING: competitions_queue key exists but is empty.") # DEBUG
                 session.pop('competitions_queue') # Clean up empty queue
                 # Fallback to repeating the last competition's parameters
                 next_competition_params = session.get('competition_params')
                 print(f"Queue was empty, falling back to reuse competition_params: {next_competition_params}") # DEBUG
            else:
                 next_competition_params = session['competitions_queue'].pop(0)
                 # Store these new params as the current ones for potential reuse later
                 session['competition_params'] = next_competition_params
                 print(f"Popped next params from queue: {next_competition_params}. Remaining queue size: {len(session['competitions_queue'])}") # DEBUG
        else:
            print("No competitions queue found. Reusing previous competition_params.") # DEBUG
            # Reuse the parameters stored in the session from the *last* competition setup
            # These might have been set initially in /competition or updated by a previous queue item
            next_competition_params = session.get('competition_params')
            print(f"Reusing params: {next_competition_params}") # DEBUG

        if not next_competition_params:
             # This is a problem state - no queue and no stored params
             flash("Error: Could not determine parameters for the next competition.", "danger")
             print("CRITICAL ERROR: No competition queue and no competition_params found in session.") # DEBUG
             return redirect(url_for('competition')) # Go back to start

        # Extract parameters for the next round
        next_mode = next_competition_params.get('mode', 1)
        next_value = next_competition_params.get('value')
        next_num_videos = next_competition_params.get('num_videos', 2)
        next_ranking_type = next_competition_params.get('ranking_type', 'winner_only')
        next_use_dynamic_weighting = next_competition_params.get('use_dynamic_weighting', False)
        next_competition_type = next_competition_params.get('competition_type', 'random')
        next_specific_videos = next_competition_params.get('videos', []) # Get specific videos if defined for next round

        print(f"--- Preparing Next Competition Call ---") # DEBUG
        print(f"Next Params: Mode={next_mode}, Value={next_value}, NumVids={next_num_videos}, RankType={next_ranking_type}, DynWeight={next_use_dynamic_weighting}, CompType={next_competition_type}, SpecificVids={next_specific_videos}") # DEBUG
        print(f"Session state: last_winner={session.get('last_winner')}") # DEBUG

        # Load the *latest* data for choosing the next videos
        # data = load_data() # Data was already loaded and updated in-place

        # --- Call choose_videos to get the next set ---
        new_competition_videos = choose_videos_function(
            data, # Use the already updated data dictionary
            next_mode,
            next_value,
            next_num_videos,
            next_use_dynamic_weighting,
            next_competition_type,
            next_specific_videos,
            session=session # Pass session for ring mode logic
        )

        print(f"Result from choose_videos for next round: {new_competition_videos}") # DEBUG
        print(f"Number of videos selected for next round: {len(new_competition_videos) if new_competition_videos else 0}") # DEBUG

        # Check if enough videos were found
        if new_competition_videos and len(new_competition_videos) >= 2:
             print(f"Sufficient videos found ({len(new_competition_videos)}). Rendering select_winner.html for next round.") # DEBUG
             # Render the competition page again with the new videos
             return render_template(
                'select_winner.html',
                competition_videos=new_competition_videos,
                num_videos=next_num_videos, # Use next params
                mode=next_mode,
                ranking_type=next_ranking_type,
                # Pass value components correctly based on next_value
                min_value=next_value.get('min_value') if isinstance(next_value, dict) else None,
                max_value=next_value.get('max_value') if isinstance(next_value, dict) else None,
                value=next_value if not isinstance(next_value, dict) else None,
                min_value1=next_value.get('min_value1') if isinstance(next_value, dict) else None,
                max_value1=next_value.get('max_value1') if isinstance(next_value, dict) else None,
                min_value2=next_value.get('min_value2') if isinstance(next_value, dict) else None,
                max_value2=next_value.get('max_value2') if isinstance(next_value, dict) else None,
                min_times_shown=next_value.get('min_times_shown') if isinstance(next_value, dict) else None, # Added for mode 9
                max_times_shown=next_value.get('max_times_shown') if isinstance(next_value, dict) else None, # Added for mode 9
                tags_filter=next_value.get('tags') if isinstance(next_value, dict) else None, # Added for mode 10
                competition_type=next_competition_type,
                data=data # Pass the updated data dictionary
            )
        else:
            # Not enough videos found for the *next* competition
            num_found = len(new_competition_videos) if new_competition_videos else 0
            flash(f"Could not find enough videos ({num_found} found, need at least 2) for the next competition based on the current criteria.", "warning")
            print(f"WARNING: Insufficient videos ({num_found}) returned by choose_videos for the next round.") # DEBUG
            # What to do now? Go back to the start competition page.
            # Clear potentially problematic state that led to no videos being found.
            session.pop('competitions_queue', None)
            session.pop('competition_params', None)
            session.pop('last_winner', None)
            print("Cleared session state (queue, params, last_winner) due to insufficient videos for next round.") # DEBUG
            return redirect(url_for('competition'))

    except Exception as e:
        # Catch any unexpected errors during processing
        flash(f"An error occurred while processing the results: {e}", "danger")
        print(f"CRITICAL ERROR in select_winner: {e}") # DEBUG
        traceback.print_exc() # Log the full traceback
        # Redirect to start page in case of error
        return redirect(url_for('competition'))



def skip_competition():
    """Skips the current competition and attempts to load the next one from the queue or repeats."""
    print("--- Entering skip_competition ---") # DEBUG

    # Logic is very similar to the 'Prepare for Next Competition' part of select_winner
    # Determine parameters for the *next* competition
    next_competition_params = None
    if session.get('competitions_queue'):
        print("Skip: Competitions queue exists.") # DEBUG
        if not session['competitions_queue']:
             print("WARNING Skip: competitions_queue key exists but is empty.") # DEBUG
             session.pop('competitions_queue')
             next_competition_params = session.get('competition_params') # Try to repeat last
             print(f"Skip: Queue empty, fallback to reuse params: {next_competition_params}") # DEBUG
        else:
             next_competition_params = session['competitions_queue'].pop(0)
             session['competition_params'] = next_competition_params # Update current params
             print(f"Skip: Popped next params from queue: {next_competition_params}. Remaining: {len(session['competitions_queue'])}") # DEBUG
    else:
        print("Skip: No competitions queue. Reusing previous competition_params.") # DEBUG
        next_competition_params = session.get('competition_params') # Repeat last
        print(f"Skip: Reusing params: {next_competition_params}") # DEBUG

    if not next_competition_params:
         flash("Error: Could not determine parameters for the next competition to skip to.", "danger")
         print("CRITICAL ERROR Skip: No queue and no competition_params found.") # DEBUG
         return redirect(url_for('competition'))

    # --- Try to load videos for the next competition ---
    data = load_data()
    if not data:
        flash("Cannot start next competition: No data loaded.", "danger")
        print("ERROR Skip: Failed to load data.") # DEBUG
        return redirect(url_for('competition'))

    # Extract parameters for the next round
    next_mode = next_competition_params.get('mode', 1)
    next_value = next_competition_params.get('value')
    next_num_videos = next_competition_params.get('num_videos', 2)
    next_ranking_type = next_competition_params.get('ranking_type', 'winner_only')
    next_use_dynamic_weighting = next_competition_params.get('use_dynamic_weighting', False)
    next_competition_type = next_competition_params.get('competition_type', 'random')
    next_specific_videos = next_competition_params.get('videos', [])

    print(f"--- Skip: Preparing Next Competition Call ---") # DEBUG
    print(f"Skip: Next Params: Mode={next_mode}, Value={next_value}, NumVids={next_num_videos}, RankType={next_ranking_type}, DynWeight={next_use_dynamic_weighting}, CompType={next_competition_type}, SpecificVids={next_specific_videos}") # DEBUG
    print(f"Skip: Session state: last_winner={session.get('last_winner')}") # DEBUG


    new_competition_videos = choose_videos_function(
        data,
        next_mode,
        next_value,
        next_num_videos,
        next_use_dynamic_weighting,
        next_competition_type,
        next_specific_videos,
        session=session
    )

    print(f"Skip: Result from choose_videos: {new_competition_videos}") # DEBUG
    print(f"Skip: Number of videos selected: {len(new_competition_videos) if new_competition_videos else 0}") # DEBUG

    if new_competition_videos and len(new_competition_videos) >= 2:
         print(f"Skip: Sufficient videos found ({len(new_competition_videos)}). Rendering select_winner.html.") # DEBUG
         flash("Skipped to the next competition.", "info")
         # Render the competition page with the new videos
         return render_template(
            'select_winner.html',
            competition_videos=new_competition_videos,
            num_videos=next_num_videos,
            mode=next_mode,
            ranking_type=next_ranking_type,
            min_value=next_value.get('min_value') if isinstance(next_value, dict) else None,
            max_value=next_value.get('max_value') if isinstance(next_value, dict) else None,
            value=next_value if not isinstance(next_value, dict) else None,
            min_value1=next_value.get('min_value1') if isinstance(next_value, dict) else None,
            max_value1=next_value.get('max_value1') if isinstance(next_value, dict) else None,
            min_value2=next_value.get('min_value2') if isinstance(next_value, dict) else None,
            max_value2=next_value.get('max_value2') if isinstance(next_value, dict) else None,
            min_times_shown=next_value.get('min_times_shown') if isinstance(next_value, dict) else None, # Added for mode 9
            max_times_shown=next_value.get('max_times_shown') if isinstance(next_value, dict) else None, # Added for mode 9
            tags_filter=next_value.get('tags') if isinstance(next_value, dict) else None, # Added for mode 10
            competition_type=next_competition_type,
            data=data
        )
    else:
        # Could not find videos even for the skipped-to competition
        num_found = len(new_competition_videos) if new_competition_videos else 0
        flash(f"Skipped, but could not find enough videos ({num_found} found, need at least 2) for the next competition based on its criteria.", "warning")
        print(f"WARNING Skip: Insufficient videos ({num_found}) found for the *next* round after skipping.") # DEBUG
        session.pop('competitions_queue', None)
        session.pop('competition_params', None)
        session.pop('last_winner', None)
        print("Skip: Cleared session state due to insufficient videos for next round.") # DEBUG
        return redirect(url_for('competition')) # Go back to start