
from llm_web_kit.input.datajson import DataJson
from llm_web_kit.extractor.extractor_chain import ExtractSimpleFactory
from func_timeout import FunctionTimedOut, func_timeout
from llm_web_kit.exception.exception import *
from realcrawl.cfg import load_pipe_tpl


class HtmlExtract:
    def __init__(self, html_file_path: str, output_format: str = "md"):
        self.config = load_pipe_tpl("extractor_pipe")
        self.extractor_chain =  ExtractSimpleFactory.create(self.config)
        self.d = {
            "track_id": "1",
            "html": open(html_file_path, "r").read(),
            "url": "https://www.google.com",
            "domain": "google.com",
            "dataset_name":"cc",
            "data_source_category":"HTML",
            "file_bytes": 4096,
            "page_layout_type": "article",
            "meta_info": {"input_datetime": "2020-01-01 00:00:00"}
        }        
        self.output_format = output_format

    def get_html_content(self):
        print("self.d: ", self.d)
        input_data = DataJson(self.d)
        data_e: DataJson = func_timeout(10, self.extractor_chain.extract, args=(input_data,))
        print("data_e: ", data_e.get_content_list().to_json())
        if self.output_format == "md":
            md_content = data_e.get_content_list().to_mm_md()
        elif self.output_format == "json":
            md_content = data_e.get_content_list().to_mm_json()
        else:
            raise ValueError(f"Invalid output format: {self.output_format}")
        return md_content

    def get_main_html(self):
        input_data = DataJson(self.d)
        data_e: DataJson = func_timeout(10, self.extractor_chain.extract, args=(input_data,))
        main_html = data_e.get_main_html()
        return main_html