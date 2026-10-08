// Optional form enhancements; every server workflow also works without JavaScript.
const adForm = document.querySelector('[data-ad-form]');
if (adForm) {
  const kind = adForm.querySelector('#id_price_type');
  const price = adForm.querySelector('#id_price');
  const updatePrice = () => {
    const fixed = kind.value === 'fixed';
    price.disabled = !fixed;
    price.required = fixed;
    price.closest('.field').style.opacity = fixed ? '1' : '.5';
  };
  kind.addEventListener('change', updatePrice);
  updatePrice();

  const upload = adForm.querySelector('#id_image');
  const preview = document.querySelector('#image-preview');
  let previousUrl;
  upload.addEventListener('change', () => {
    if (previousUrl) URL.revokeObjectURL(previousUrl);
    const file = upload.files[0];
    preview.hidden = !file || !file.type.startsWith('image/');
    if (!preview.hidden) {
      previousUrl = URL.createObjectURL(file);
      preview.querySelector('img').src = previousUrl;
    }
  });
}
