// Вопросы в виде переписки: по нажатию вопрос «отправляется», основатель «печатает»,
// затем пузырь плавно раздвигается до ответа. Без JS это обычные <details>.

const EASE = 'cubic-bezier(0.22, 0.8, 0.2, 1)';
const TYPING_MS = 750;

export function initFaq(root, { reduced = false } = {}) {
  if (!root || reduced) return;

  root.querySelectorAll('details').forEach((item) => {
    const summary = item.querySelector('summary');
    const body = item.querySelector('.qa__a');
    const bubble = item.querySelector('.qa__bubble');
    let anim = null;
    let timer = 0;

    const close = () => {
      clearTimeout(timer);
      item.classList.add('is-closing');
      anim = body.animate(
        [{ height: `${body.offsetHeight}px`, opacity: 1 }, { height: '0px', opacity: 0 }],
        { duration: 380, easing: EASE }
      );
      anim.onfinish = () => {
        item.open = false;
        item.classList.remove('is-closing', 'is-typing', 'is-answered');
        anim = null;
      };
    };

    const open = () => {
      item.classList.remove('is-closing', 'is-answered');
      item.classList.add('is-typing');
      item.open = true;
      anim = body.animate(
        [{ height: '0px', opacity: 0 }, { height: `${body.offsetHeight}px`, opacity: 1 }],
        { duration: 420, easing: EASE }
      );
      anim.onfinish = () => { anim = null; };

      // Пузырь «печатает», затем раздвигается до текста ответа (FLIP по размеру)
      timer = setTimeout(() => {
        const from = bubble.getBoundingClientRect();
        item.classList.remove('is-typing');
        item.classList.add('is-answered');
        const to = bubble.getBoundingClientRect();
        bubble.animate(
          [{ width: `${from.width}px`, height: `${from.height}px` }, { width: `${to.width}px`, height: `${to.height}px` }],
          { duration: 420, easing: EASE }
        );
      }, TYPING_MS);
    };

    summary.addEventListener('click', (e) => {
      e.preventDefault();
      anim?.cancel();
      if (item.open && !item.classList.contains('is-closing')) close();
      else open();
    });
  });
}
