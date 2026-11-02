import numpy as np

from doorlock.faces import SIZE, FaceModel, photo_count, save_face


def pattern(seed):
    # one texture per fake person
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 255, (25, 25), dtype=np.uint8)
    return np.kron(base, np.ones((8, 8), np.uint8))[: SIZE[1], : SIZE[0]]


def test_train_and_predict(data_dir):
    for pid in (1, 2):
        for i in range(5):
            noisy = np.clip(pattern(pid).astype(int) + np.random.default_rng(i).integers(-10, 10, SIZE), 0, 255).astype(np.uint8)
            save_face(pid, noisy, i)
    model = FaceModel()
    assert model.train() == 10 and photo_count(1) == 5
    assert model.predict(pattern(1))[0] == 1
    assert model.predict(pattern(2))[0] == 2


def test_model_is_saved_and_reloaded(data_dir):
    save_face(7, pattern(7), 0)
    FaceModel().train()
    assert FaceModel().trained


def test_no_photos_means_untrained(data_dir):
    model = FaceModel()
    assert model.train() == 0
    assert model.predict(pattern(1)) == (None, None)


def test_blank_frame_has_no_face(data_dir):
    boxes, _ = FaceModel().find(np.zeros((480, 640, 3), np.uint8))
    assert boxes == []
