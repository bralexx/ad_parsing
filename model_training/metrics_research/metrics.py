import numpy as np
import evaluate

def try_convert_types(var1, var2):
  type1 = type(var1)
  type2 = type(var2)
  if type1 != type2:
      try:
          var1_to_var2_type = type2(var1)
          return var1_to_var2_type, var2
      except (ValueError, TypeError) as e:
        pass
      try:
          var2_to_var1_type = type1(var2)
          return var1, var2_to_var1_type
      except (ValueError, TypeError) as e:
        pass
  return var1, var2

def process_str(var):
  if isinstance(var, str):
    var = var.strip()
  return var

def price_eq(bundle1, bundle2):
  price1 = bundle1['Price']
  price2 = bundle2['Price']
  price1, price2 = try_convert_types(price1, price2)
  try:
    price1_val = float(price1)
    price2_val = float(price2)
    return price1_val == price2_val
  except Exception:
    pass
  price1 = process_str(price1)
  price2 = process_str(price2)
  return price1 == price2

cur_aliases = {
    'EUR': ['eur', 'euro', 'евр', 'евро', '€'],
    'GEL': ['LAR', 'Lari', 'gel', 'lari', 'л', 'лар', 'лари', 'ларри', 'ლ',  '₾'],
    'RUB': ['₽', 'р', 'руб'],
    'USD': ['$'],
    'UAH': ['грн']
  }
for key in cur_aliases.keys():
  cur_aliases[key].append(key)
inverse_currency_aliases = {alias:code for code, aliases in cur_aliases.items() for alias in aliases}

def currency_eq(bundle1, bundle2):
  cur1 = bundle1['Currency'].strip()
  cur2 = bundle2['Currency'].strip()
  if cur1 not in inverse_currency_aliases:
    return False
  else:
    cur1 = inverse_currency_aliases[cur1]
  if cur2 not in inverse_currency_aliases:
    return False
  else:
    cur2 = inverse_currency_aliases[cur2]
  return cur1 == cur2

def count_eq(bundle1, bundle2):
  count1 = bundle1['Count']
  count2 = bundle2['Count']
  count1, count2 = try_convert_types(count1, count2)
  count1 = process_str(count1)
  count2 = process_str(count2)
  return count1 == count2

bleu_metric = evaluate.load("sacrebleu")
def title_bleu(bundle1, bundle2):
  return bleu_metric.compute(predictions=[bundle2['Title']], references=[[bundle1['Title']]])['score']

chrf_metric = evaluate.load("chrf")
def title_chrf(bundle1, bundle2):
  return chrf_metric.compute(predictions=[bundle2['Title']], references=[[bundle1['Title']]])['score']

def product(bundle1, bundle2):
  res = 1.0
  res *= price_eq(bundle1, bundle2)
  res *= currency_eq(bundle1, bundle2)
  res *= count_eq(bundle1, bundle2)
  res *= title_chrf(bundle1, bundle2) / 100
  return res


def first_bundle_apply_gen(func, ret_nan=False):
  def wrapped(bundles1, bundles2):
    if len(bundles1) != 1 or len(bundles2) != 1:
      return False if not ret_nan else np.nan
    return func(bundles1[0], bundles2[0])
  return wrapped

def best_match_multi_bundle_apply_gen(func, spec_title_aggr=None, ret_best_pairs=False):
  def wrapped(ref_bundles, pred_bundles):
    ids_refs = list(range(len(ref_bundles)))
    ids_preds = list(range(len(pred_bundles)))
    best_match = []
    scores = []
    while len(ids_refs) > 0 and len(ids_preds) > 0:
      pairs = [(i, j) for i in ids_refs for j in ids_preds]
      best_pair = max(pairs, key=lambda pair: func(ref_bundles[pair[0]], pred_bundles[pair[1]]))
      ids_refs = [i for i in ids_refs if i != best_pair[0]]
      ids_preds = [i for i in ids_preds if i != best_pair[1]]
      best_match.append(best_pair)
    if ret_best_pairs:
      return best_match
    if spec_title_aggr is None:
      scores = [func(ref_bundles[pair[0]], pred_bundles[pair[1]]) for pair in best_match]
      for _ in ids_refs + ids_preds:
        scores.append(0)
    else:
      if len(best_match) == 0:
        return 0
      try:
        refs = [[ref_bundles[pair[0]]['Title']] for pair in best_match]
        preds = [pred_bundles[pair[1]]['Title'] for pair in best_match]
      except Exception as e:
        print(best_match, len(preds), len(refs))
        raise e
      return spec_title_aggr.compute(predictions=preds, references=refs)['score']
    return np.mean(scores)
  return wrapped

metrics = {
  'BEP-sb': first_bundle_apply_gen(product, ret_nan=True),
  'BEP-multi': best_match_multi_bundle_apply_gen(product),
  'TA-BLEU-sb': first_bundle_apply_gen(title_bleu, ret_nan=True),
  'TA-CHRF-sb': first_bundle_apply_gen(title_chrf, ret_nan=True),
  'TA-CHRF-multi': best_match_multi_bundle_apply_gen(title_chrf, spec_title_aggr=chrf_metric),
  'EB-ind': lambda bundles1, bundles2: len(bundles1) < len(bundles2),
  'MB-ind':lambda bundles1, bundles2: len(bundles1) > len(bundles2)
}

def calc_bundles_metrics(preds, refs):
  assert len(preds) == len(refs)
  results = {}
  for key, func in metrics.items():
    metric_values = []
    for i in range(len(preds)):
      pred = preds[i]
      ref = refs[i]
      metric_values.append(func(ref, pred))
    metric_values = [val for val in metric_values if val is not np.nan]
    results[key] = np.mean(metric_values)
  sb_title_preds = []
  sb_title_refs = []
  mb_title_preds = []
  mb_title_refs = []
  for i in range(len(preds)):
    if len(preds[i]) == 1 and len(refs[i]) == 1:
      sb_title_preds.append(preds[i][0]['Title'])
      sb_title_refs.append([refs[i][0]['Title']])
    best_pairs = best_match_multi_bundle_apply_gen(title_chrf, ret_best_pairs=True)(refs[i], preds[i])
    try:
      for ref_i, pred_i in best_pairs:
        mb_title_preds.append(preds[i][pred_i]['Title'])
        mb_title_refs.append([refs[i][ref_i]['Title']])
    except Exception as e:
      print(best_pairs)
      raise e

  results['BLEU-classic'] = bleu_metric.compute(predictions=sb_title_preds, references=sb_title_refs)['score'] if len(sb_title_preds) > 0 else 0
  results['CHRF-classic'] = chrf_metric.compute(predictions=sb_title_preds, references=sb_title_refs)['score'] if len(sb_title_preds) > 0 else 0
  
  results['CHRF-classic-multi'] = chrf_metric.compute(predictions=mb_title_preds, references=mb_title_refs)['score'] if len(mb_title_preds) > 0 else 0
  return results
