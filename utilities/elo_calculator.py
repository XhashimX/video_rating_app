def calculate_expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 800))


def update_ratings_multiple(ranked_videos, data, K=54):
    """
    Updates ratings based on ranked videos.
    ranked_videos: list of tuples (video_name, current_rating, rank_index)
    """
    # Create a copy to calculate expected scores based on start-of-round ratings
    # This prevents the order of processing from affecting the results within the same round
    current_round_ratings = {vid: rating for vid, rating, rank in ranked_videos}

    for i, (vid_i, _, rank_i) in enumerate(ranked_videos):
        for j, (vid_j, _, rank_j) in enumerate(ranked_videos[i + 1:], i + 1):
            
            # --- START: MODIFIED SECTION ---
            # إذا كان الفيديوهان لهما نفس الترتيب (كلاهما خاسر مثلاً في وضع Winner Only)
            # نتجاهل الحساب بينهما تماماً لمنع "التعادل" غير المرغوب فيه
            if rank_i == rank_j:
                continue
            # --- END: MODIFIED SECTION ---

            rating_i = current_round_ratings[vid_i]
            rating_j = current_round_ratings[vid_j]

            if rank_i < rank_j:
                score_i = 1
                score_j = 0
            elif rank_i > rank_j:
                score_i = 0
                score_j = 1
            else:
                score_i = 0.5
                score_j = 0.5

            expected_i = calculate_expected_score(rating_i, rating_j)
            expected_j = calculate_expected_score(rating_j, rating_i)

            # K-Factor Logic
            if score_i > score_j:  # Player i wins
                if data[vid_i]['win_streak'] >= 3:
                    K_i = 100 + (data[vid_i]['win_streak'] - 3) * 30
                else:
                    K_i = K
                K_j = K
            elif score_i < score_j:  # Player j wins
                if data[vid_i]['loss_streak'] >= 3:
                    K_i = 100 + (data[vid_i]['loss_streak'] - 3) * 30
                else:
                    K_i = K
                if data[vid_j]['win_streak'] >= 3:
                    K_j = 100 + (data[vid_j]['win_streak'] - 3) * 30
                else:
                    K_j = K
            else:  # Draw
                K_i = K
                K_j = K

            delta_i = K_i * (score_i - expected_i)
            delta_j = K_j * (score_j - expected_j)

            data[vid_i]['rating'] += delta_i
            data[vid_j]['rating'] += delta_j

            # Streak Logic Update
            if score_i > score_j:
                data[vid_i]['win_streak'] += 1
                data[vid_i]['loss_streak'] = 0
                data[vid_j]['loss_streak'] += 1
                data[vid_j]['win_streak'] = 0
            elif score_i < score_j:
                data[vid_i]['loss_streak'] += 1
                data[vid_i]['win_streak'] = 0
                data[vid_j]['win_streak'] += 1
                data[vid_j]['loss_streak'] = 0
            # في حالة التعادل أو التخطي (بسبب شرط rank_i == rank_j) لا نعدل الستريك