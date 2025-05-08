from lite_avatar import liteAvatar

class AvatarImageProcessor:
    def __init__(self, data_dir="./data/preload", fps=30, use_gpu=False):
        self.avatar = liteAvatar(
            data_dir=data_dir,
            generate_offline=True,
            use_gpu=use_gpu,
            fps=fps
        )
        self.fps = fps
        self.idle_param = self.avatar.get_idle_param()
