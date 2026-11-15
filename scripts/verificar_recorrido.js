async page => {
  const check = (condition, message) => { if (!condition) throw new Error(message); };
  const results = [];
  for (const viewport of [{width:1280,height:800},{width:390,height:844},{width:360,height:740}]) {
    await page.setViewportSize(viewport);
    await page.goto('http://127.0.0.1:4180/');
    const spanish = page.getByRole('button',{name:'Cambiar a español',exact:true});
    if (await spanish.count()) await spanish.click();
    await page.locator('#tour-open').click({timeout:10000});
    const dialog = page.locator('dialog.tour');
    await dialog.waitFor();
    check((await dialog.innerText()).includes('2001–2024'), 'Falta periodo nacional');
    await dialog.locator('[data-next]').click();
    const counts=[];
    for (const t of ['0.5','1','2','5']) {
      await dialog.locator(`[data-threshold="${t}"]`).click();
      counts.push(await dialog.locator('.tour-number strong').innerText());
    }
    check(counts.join('|')==='202 / 442|160 / 442|64 / 442|0 / 442', 'Umbrales incorrectos: '+counts);
    check((await dialog.innerText()).includes('0 disputas no demuestra acuerdo'), 'Falta limite de potencia');
    await dialog.locator('[data-next]').click();
    const baseline=await dialog.locator('.tour-stats').innerText();
    check(baseline.includes('7/8')&&baseline.includes('39'), 'Falta regla base');
    await dialog.locator('[data-confirm="true"]').click();
    const stats=await dialog.locator('.tour-stats').innerText();
    check(stats.includes('6/8')&&stats.includes('16')&&stats.includes('0/8'), 'Resultado corregido incorrecto');
    await dialog.getByText('Ver los 8 eventos y sus fechas',{exact:true}).click();
    check(await dialog.locator('tbody tr').count()===8, 'Faltan eventos');
    check((await dialog.locator('tbody').innerText()).includes('2022-09'), 'Falta evento perdido');
    await dialog.getByText('Mostrar evidencia y límites',{exact:true}).click();
    check((await dialog.innerText()).includes('GOES: sin resolver'), 'GOES desactualizado');
    const downloadPromise=page.waitForEvent('download');
    await dialog.locator('[data-download]').click();
    const download=await downloadPromise;
    check(download.suggestedFilename()==='stellar-horizons-evidencia.json', 'Descarga ausente');
    const geometry=await dialog.evaluate(el=>({width:el.clientWidth,content:el.scrollWidth}));
    check(geometry.content<=geometry.width+1,'Desbordamiento horizontal del dialogo');
    await dialog.evaluate(el=>el.scrollTop=0);
    await page.screenshot({path:`reports_nacional/recorrido-yuna-${viewport.width}.png`});
    await page.keyboard.press('Escape');
    check(await dialog.count()===0,'Escape no cierra');
    check(await page.locator('#tour-open').evaluate(el=>el===document.activeElement),'No restaura foco');
    results.push({viewport,counts,baseline,confirmed:stats,download:download.suggestedFilename()});
  }
  // Verificar traduccion y cierre por el boton final.
  await page.getByRole('button',{name:'Switch to English',exact:true}).click();
  await page.locator('#tour-open').click();
  const dialog=page.locator('dialog.tour');
  check((await dialog.innerText()).includes('Is rainfall changing?'),'Falta traduccion');
  await dialog.locator('[data-next]').click();
  await dialog.locator('[data-next]').click();
  await dialog.getByRole('button',{name:'Return to map',exact:true}).click();
  check(await dialog.count()===0,'No regresa al mapa');
  return {passed:true,results,english:true};
}
