# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/05_bayes_inference.ipynb (unless otherwise specified).

__all__ = ['entropy', 'uncertainty_best_probability', 'BALD', 'top_k_uncertainty', 'plot_hist_groups']

# Cell
from fastai.callback.preds import MCDropoutCallback
from fastai.learner import Learner
from fastcore.foundation import patch, L
from fastai.torch_core import to_np

# Cell
from collections import Counter
import seaborn as sns
import torch

# Cell
def entropy(probs):
    """Return the prediction of a T*N*C tensor with :
        - T : the number of samples
        - N : the batch size
        - C : the number of classes
    """
    mean_probs = probs.mean(dim=0)
    entrop = - (torch.log(mean_probs) * mean_probs).sum(dim=1)
    return entrop

def uncertainty_best_probability(probs):
    """Return the standard deviation of the most probable class"""
    idx = probs.mean(dim=0).argmax(dim=1)

    std = probs[:, torch.arange(len(idx)), idx].std(dim=0)

    return std

def BALD(probs):
    """Information Gain, distance between the entropy of averages and average of entropy"""
    entrop1 = entropy(probs)
    entrop2 = - (torch.log(probs) * probs).sum(dim=2)
    entrop2 = entrop2.mean(dim=0)

    ig = entrop1 - entrop2
    return ig

def top_k_uncertainty(s, k=5, reverse=True):
    """Return the top k indexes"""
    sorted_s = sorted(list(zip(torch.arange(len(s)), s)),
                      key=lambda x: x[1], reverse=reverse)
    output = [sorted_s[i][0] for i in range(k)]

def plot_hist_groups(pred,y,metric,bins=None,figsize=(16,16)):
    TP = to_np((pred.mean(dim=0).argmax(dim=1) == y) & (y == 1))
    TN = to_np((pred.mean(dim=0).argmax(dim=1) == y) & (y == 0))
    FP = to_np((pred.mean(dim=0).argmax(dim=1) != y) & (y == 0))
    FN = to_np((pred.mean(dim=0).argmax(dim=1) != y) & (y == 1))

    result = metric(pred)

    TP_result = result[TP]
    TN_result = result[TN]
    FP_result = result[FP]
    FN_result = result[FN]

    fig,ax = plt.subplots(2,2,figsize=figsize)

    sns.distplot(TP_result,ax=ax[0,0],bins=bins)
    ax[0,0].set_title(f"True positive")

    sns.distplot(TN_result,ax=ax[0,1],bins=bins)
    ax[0,1].set_title(f"True negative")

    sns.distplot(FP_result,ax=ax[1,0],bins=bins)
    ax[1,0].set_title(f"False positive")

    sns.distplot(FN_result,ax=ax[1,1],bins=bins)
    ax[1,1].set_title(f"False negative")
    return output

# Cell
@patch
def bayes_get_preds(self:Learner, ds_idx=1, dl=None, n_sample=10,
                    act=None,with_loss=False, **kwargs):
    """Get MC Dropout predictions from a learner, and eventually reduce the samples"""
    cbs = [MCDropoutCallback()]
    if 'cbs' in kwargs:
        kw_cbs = kwargs.pop('cbs')
        if 'MCDropoutCallback' not in L(kw_cbs).attrgot('name'):
            cbs = kw_cbs + cbs
    preds = []
    with self.no_bar():
        for i in range(n_sample):
            pred, y = self.get_preds(ds_idx=ds_idx,dl=dl,act=act,
                                     with_loss=with_loss, cbs=cbs, **kwargs)
            # pred = n_dl x n_vocab
            preds.append(pred)
    preds = torch.stack(preds)
    ents = entropy(preds)
    mean_preds = preds.mean(dim=0)
    max_preds = mean_preds.max(dim=1)
    best_guess = max_preds.indices
    best_prob = max_preds.values
    best_cat = L(best_guess,use_list=True).map(lambda o: self.dls.vocab[o.item()])
    return preds, mean_preds, ents,best_guess, best_prob, best_cat

# Cell
@patch
def bayes_predict(self:Learner,item, rm_type_tfms=None, with_input=False,
                  sample_size=10,reduce=True):
    "gets a sample distribution of predictions and computes entropy"
    dl = self.dls.test_dl([item], rm_type_tfms=rm_type_tfms, num_workers=0)

    # modify get_preds to get distributed samples
    collect_preds = []
    collect_targs = []
    collect_dec_preds = []
    collect_inp = None
    cbs = [MCDropoutCallback()]
    with self.no_bar():
        for j in range(sample_size):
            inp,preds,_,dec_preds = self.get_preds(dl=dl, with_input=True,
                                                   with_decoded=True,
                                                   cbs=cbs)
            i = getattr(self.dls, 'n_inp', -1)
            inp = (inp,) if i==1 else tuplify(inp)
            dec = self.dls.decode_batch(inp + tuplify(dec_preds))[0]
            dec_inp,dec_targ = map(detuplify, [dec[:i],dec[i:]])
            # res = dec_targ,dec_preds[0],preds[0]
            if with_input and collect_inp is None: # collect inp first iter only
                   collect_inp = dec_inp
            collect_targs.append(dec_targ)
            collect_dec_preds.append(dec_preds[0])
            collect_preds.append(preds[0])
    dist_preds = torch.stack(collect_preds)
    dist_dec_preds = L(collect_dec_preds).map(lambda o: o.item())
    dist_targs = L(collect_targs)
    res1 = (dist_targs, dist_dec_preds, dist_preds)

    mean_pred = dist_preds.mean(dim=0)
    ent = entropy(dist_preds.unsqueeze(1)).item()
    best_guess = torch.argmax(mean_pred).item()
    best_prob = mean_pred[best_guess].item()
    best_cat = self.dls.vocab[best_guess]
    res2 = (ent, best_prob, best_guess, best_cat)

    if reduce:
        if len(dist_targs.unique()) > 1:
            targ = Counter(dist_targs)
        else:
            targ = dist_targs.unique()[0]

        if len(dist_dec_preds.unique()) > 1:
            dec_pred = Counter(dist_dec_preds)
        else:
            dec_pred = dist_dec_preds.unique()[0]
        res1 = (targ, dec_pred, mean_pred)

    res = res1 + res2
    if with_input:
        res = (collect_inp,) + res
    return res


# Cell
@patch
def bayes_predict_with_uncertainty(self:Learner, item, rm_type_tfms=None, with_input=False, threshold_entropy=0.2, sample_size=10, reduce=True):
    "gets prediction results plus if prediction passes entropy threshold"
    res = self.bayes_predict(item,rm_type_tfms=rm_type_tfms,
                             with_input=with_input, sample_size=sample_size,
                             reduce=reduce)
    ent = res[4] if with_input else res[3]
    return (ent < threshold_entropy,) + res