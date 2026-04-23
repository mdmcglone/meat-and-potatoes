import time
import os
import pytest
def test_img_to_graph():
    from graph_to_times import image_to_graph
    image_to_graph(
        image_path="test_imgs/screenshot_cropped_filtered.png",
        show_plot=False,  # do not display; just save plots
        save_raw_plot_path="test_imgs/graph_pixels.png",
        save_filtered_plot_path="test_imgs/graph.png"
    )
    
    assert os.path.isfile("test_imgs/graph_pixels.png")
    assert os.path.isfile("test_imgs/graph.png")
    assert os.path.getmtime("test_imgs/graph_pixels.png") > time.time() - 1
    assert os.path.getmtime("test_imgs/graph.png") > time.time() - 1
    
def test_img_to_graph_error():
    from graph_to_times import image_to_graph
    
    with pytest.raises(FileNotFoundError):
        image_to_graph(
            image_path="test_imgs/DNE.png",
            show_plot=False,  # do not display; just save plots
            save_raw_plot_path="test_imgs/graph_pixels.png",
            save_filtered_plot_path="test_imgs/graph.png"
        )
        
    
@pytest.mark.parametrize("time_text,res, error", [
    ("3:4", 184, None),
    ("3:4:5", (3*3600) +(4*60) + 5, None),
    ("4000:4000", 4000*60 + 4000, None),
    ("124:40:5", (3600*124) + (40*60) + 5, None),
    ("4000:4000:4000", (4000*3600) + (4000*60) + 4000, None),
    ("abc:def", None, ValueError)
    
])
def test_parse_time_to_seconds(time_text, res, error):
    from graph_to_times import parse_time_to_seconds
    if error is not None:
        with pytest.raises(error):
            parse_time_to_seconds(time_text)
    else:
        assert parse_time_to_seconds(time_text) == res
        
        


