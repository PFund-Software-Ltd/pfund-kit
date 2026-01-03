import time
from pfund_kits.progress_bar import track, ProgressBar
from pfund_kits.utils import RichColor, RichTextStyle


if __name__ == "__main__":

    print("\n=== Example 1: Different bar_style and progress_style ===")
    with ProgressBar(
        total=5,
        description="Notice the colors",
        bar_style=RichColor.YELLOW,           # ← Colors the BAR itself (━━━━━━)
        progress_style=(RichTextStyle.STRIKE + RichColor.RED).value  # ← Colors the "100%" text
    ) as pb:
        for i in range(5):
            time.sleep(0.3)
            pb.advance()

    # print("\n=== Example 2: Same color for both ===")
    # with ProgressBar(
    #     total=5,
    #     description="Everything cyan",
    #     bar_style=RichColor.CYAN,
    #     progress_style=RichColor.CYAN.value  # Same color as bar
    # ) as pb:
    #     for i in range(5):
    #         time.sleep(0.3)
    #         pb.advance()

    # # print("\n=== Example 3: Extreme contrast ===")
    # with ProgressBar(
    #     total=5,
    #     description="High contrast example",
    #     bar_style=RichColor.BRIGHT_YELLOW.value,      # Bright yellow bar
    #     progress_style=(RichTextStyle.DIM + RichColor.MAGENTA).value  # Bold magenta percentage
    # ) as pb:
    #     for i in range(5):
    #         time.sleep(0.3)
    #         pb.advance()