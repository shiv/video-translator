from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

from app import logger
from app.services.translation.translation import Translation


class TranslationNLLB(Translation):

    def __init__(self, device="cpu"):
        super().__init__(device)
        self.translator = None
        self.translator_languages = ""

    def load_model(self, name="nllb-200-1.3B"):
        self.model_name = f"facebook/{name}"
        self.tokenizer = self._get_tokenizer_nllb()

    def _translate_text(
        self, source_language: str, target_language: str, text: str
    ) -> str:
        languages = f"{source_language}{target_language}"
        if not self.translator or self.translator_languages != languages:
            model = self._get_model_nllb()
            self.translator = pipeline(
                "translation",
                model=model,
                tokenizer=self.tokenizer,
                src_lang=self._get_nllb_language(source_language),
                tgt_lang=self._get_nllb_language(target_language),
                max_length=1024,
            )
            self.translator_languages = languages

        translated = self.translator(text)
        return translated[0]["translation_text"]

    def _get_tokenizer_nllb(self):
        return AutoTokenizer.from_pretrained(self.model_name)

    def _get_model_nllb(self):
        try:
            return AutoModelForSeq2SeqLM.from_pretrained(self.model_name).to(
                self.device
            )
        except RuntimeError as e:
            if self.device == "cuda":
                logger().warning(
                    f"Loading translation model {self.model_name} in CPU since cannot be load in GPU"
                )
                return AutoModelForSeq2SeqLM.from_pretrained(self.model_name).to("cpu")
            else:
                raise e

    def get_language_pairs(self):
        tokenizer = self._get_tokenizer_nllb()
        # Returns 'cat_Latn'
        original_list = tokenizer.additional_special_tokens
        # Get only the language codes
        supported_languages = [s[:3] for s in original_list]
        pairs = set()
        for source in supported_languages:
            for target in supported_languages:
                if source == target:
                    continue

                pair = (source, target)
                pairs.add(pair)

        return pairs

    def _get_nllb_language(self, source_language_iso_639_3: str) -> str:
        tokenizer = self._get_tokenizer_nllb()
        nllb_languages = tokenizer.additional_special_tokens
        for nllb_language in nllb_languages:
            if nllb_language[:3] == source_language_iso_639_3:
                return nllb_language

        raise ValueError(
            f"Language {source_language_iso_639_3} not supported by Meta NLLB translation model"
        )
