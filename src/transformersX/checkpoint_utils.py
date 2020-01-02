import os
import glob
import logging
import torch

from transformers import WEIGHTS_NAME

STEP_CKPT = 'checkpoint-{}'
LAST_CKPT = 'checkpoint-last'
BEST_CKPT = 'checkpoint-best'
ARGS_CKPT = 'training_args.bin'
OPTIMIZER_CKPT = 'optimizer.pt'
SCHEDULER_CKPT = 'scheduler.pt'


def save_checkpoint(args, model, global_step, eval_results=None, tokenizer=None, optimizer=None, scheduler=None):
    output_dirs = []
    if args.save_all_checkpoints:
        output_dirs = [os.path.join(args.output_dir, STEP_CKPT.format(global_step))]

    if args.save_last_checkpoint:
        output_dirs.append(os.path.join(args.output_dir, LAST_CKPT))

    if args.save_best_checkpoint and eval_results is not None:
        # Get the metric for best checkpoint
        eval_metric = eval_results[args.best_checkpoint_metric] if isinstance(eval_results, dict) else eval_results
        prev_best = getattr(save_checkpoint, "best", eval_metric)

        is_better = (lambda x, y: x >= y) if args.maximize_best_checkpoint_metric else (lambda x, y: x <= y)
        if is_better(eval_metric, prev_best):
            save_checkpoint.best = eval_metric
            output_dirs.append(os.path.join(args.output_dir, BEST_CKPT))

    for output_dir in output_dirs:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        else:
            for fn in os.listdir(output_dir):  # clean the directory
                os.remove(os.path.join(output_dir, fn))

        logging.info("Saving model checkpoint to %s", output_dir)
        model_to_save = model.module if hasattr(model, 'module') else model  # Take care of distributed/parallel training
        model_to_save.save_pretrained(output_dir)
        torch.save(args, os.path.join(output_dir, ARGS_CKPT))

        if tokenizer is not None:
            tokenizer.save_pretrained(output_dir)
        if optimizer is not None:
            torch.save(optimizer.state_dict(), os.path.join(output_dir, OPTIMIZER_CKPT))
        if scheduler is not None:
            torch.save(scheduler.state_dict(), os.path.join(output_dir, SCHEDULER_CKPT))

    return output_dirs


def get_trained_checkpoints(args):
    checkpoints = []
    if args.save_all_checkpoints:
        checkpoints = list(
            os.path.dirname(c) for c in sorted(glob.glob(args.output_dir + '/**/' + WEIGHTS_NAME, recursive=True)))
        logging.getLogger("transformers.modeling_utils").setLevel(logging.WARN)  # Reduce model loading logs
    else:
        if args.save_last_checkpoint:
            checkpoints.append(os.path.join(args.output_dir, LAST_CKPT))
        if args.save_best_checkpoint:
            checkpoints.append(os.path.join(args.output_dir, BEST_CKPT))
        checkpoints = [c for c in checkpoints if os.path.exists(os.path.join(c, WEIGHTS_NAME))]

    return checkpoints
