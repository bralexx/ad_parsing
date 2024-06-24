import torch
import sys
sys.path.append('../metrics_research')
from metrics import calc_bundles_metrics
import numpy as np
from json_format import JSONProcessor
import evaluate
bleu_metric = evaluate.load("sacrebleu")

class Evaluator:
  def __init__(self, df, model, tokenizer, use_cache=False, json_processor=JSONProcessor(), batch_size=8, seq_tokens=False):
    # self.gen_kwargs = gen_kwargs
    self.json_processor = json_processor
    self.model = model
    self.tokenizer = tokenizer
    self.seq_tokens = seq_tokens
    self.batch_size=batch_size
    self.df = df
    self.failed_generations = 0
    self.use_cache = use_cache
    if use_cache:
      self.cache = {}

  # def generate_text(self, input_text, device='cuda'):
  #   if self.use_cache and input_text in self.cache:
  #     return self.cache[input_text]
  #   input_ids = self.tokenizer.encode(input_text, return_tensors="pt").to(device)
  #   # model.eval()
  #   # input_ids = torch.IntTensor([input_ids['input_ids']]).to(device)
  #   with torch.no_grad():
  #     outputs = self.model.generate(input_ids, max_length=128, early_stopping=True)
  #     decoded_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
  #     try:
  #       json = self.unprocess_json(decoded_output)
  #     except:
  #       json = []
  #       self.failed_generations += 1
  #     # generated_ids = model.generate(input_ids, max_length=512)
  #   if self.use_cache:
  #     self.cache[input_text] = json
  #   return json

  def generate_text_batch(self, input_texts, device='cuda'):
    if not isinstance(input_texts, list):
        raise ValueError("input_texts should be a list of strings")
    if self.seq_tokens:
      input_texts = [self.tokenizer.bos_token + t + self.tokenizer.eos_token for t in input_texts]
    encoded = self.tokenizer(input_texts, return_tensors="pt", padding=True, truncation=True, max_length=128)
    input_ids = encoded.input_ids.to(device)
    attention_mask = encoded.attention_mask.to(device)

    with torch.no_grad():
        outputs = self.model.generate(input_ids, attention_mask=attention_mask, max_length=150, early_stopping=True)
        decoded_outputs = [self.tokenizer.decode(output, skip_special_tokens=True) for output in outputs]
        results = []
        for decoded_output in decoded_outputs:
            try:
                json_output = self.json_processor.unprocess_json(decoded_output)
            except Exception as e:
                json_output = []
                self.failed_generations += 1
            results.append(json_output)
            if self.use_cache:
                for input_text, result in zip(input_texts, results):
                    self.cache[input_text] = result

    return results
  
  # def generate_samples(self, ids=None, count=None):
  #   if count is not None:
  #     ids = self.df.index[:count]
  #   if ids is None:
  #     ids = self.df.index

  #   results = {}
  #   for i in ids:
  #     input_text = self.df.loc[i, 'Text']
  #     pred = self.generate_text(input_text)
  #     if len(pred) == 0 or 'Title' not in pred[0]:
  #       self.failed_generations += 1
  #       results[i] = []
  #     else:
  #       results[i] = pred
  #   return results
  
  def generate_samples_batched(self, ids=None, count=None, batch_size=8):
    if count is not None:
        ids = self.df.index[:count]
    if ids is None:
        ids = self.df.index

    results = {}
    all_texts = [self.df.loc[i, 'Text'] for i in ids]
    all_ids = list(ids)
    
    for start in range(0, len(all_texts), batch_size):
        end = start + batch_size
        batch_texts = all_texts[start:end]
        batch_ids = all_ids[start:end]
        
        predictions = self.generate_text_batch(batch_texts)
        
        for i, pred in zip(batch_ids, predictions):
            if len(pred) == 0 or 'Title' not in pred[0]:
                results[i] = []
            else:
                results[i] = pred
                
    return results
  
  # def calc_bleu(self):
  #   self.failed_generations = 0
  #   refs = []
  #   predictions = []
  #   full_predictions = self.generate_samples()
  #   for i, pred in full_predictions:
  #     if len(pred) == 1 and 'Title' in pred[0]:
  #       refs.append([self.df.loc[i, 'Title']])
  #       predictions.append(pred[0]['Title'])
  #   bleu_value = bleu_metric.compute(predictions=predictions, references=refs)
  #   return {'bleu': bleu_value, 'failed_ratio': self.failed_generations / len(self.df)}
  
  def calc_bleu_batched(self):
    self.failed_generations = 0
    refs = []
    preds = []
    json_refs = []
    json_preds = []
    full_predictions = self.generate_samples_batched(batch_size=self.batch_size)
    
    for i, pred in full_predictions.items():
      json_refs.append(self.df.loc[i, 'json'])
      json_preds.append(pred)
      if len(self.df.loc[i, 'json']) == 1 and len(pred) == 1:
        refs.append([self.df.loc[i, 'json'][0]['Title']])
        preds.append(pred[0]['Title'])
    
    if len(refs) != 0:
      bleu_value = bleu_metric.compute(predictions=preds, references=refs)['score']
    else:
      bleu_value = np.nan

    results = calc_bundles_metrics(refs=json_refs, preds=json_preds)
    results.update({'bleu_old': bleu_value, 'failed_ratio': self.failed_generations / len(self.df)})
    return results
