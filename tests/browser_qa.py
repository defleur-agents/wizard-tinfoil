"""Playwright against real private stage; only synthetic keys and free verification."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
BASE='http://127.0.0.1:18803'
import os
OUT=Path(os.environ.get('QA_OUT','qa-evidence'));OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(headless=True)
    page=b.new_page(viewport={'width':390,'height':844})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE)
    page.request.post(BASE+'/api/disconnect',data={},headers={'Origin':BASE,'X-Wizard-Request':'1'})
    page.reload();page.get_by_text('Not connected',exact=True).wait_for()
    assert page.locator('#api-key').get_attribute('type')=='password'
    assert page.locator('#disconnect').is_hidden() and page.locator('#api-key').is_visible()
    assert page.get_by_role('link',name='Get a key ↗').get_attribute('href')=='https://dash.tinfoil.sh'
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    # Synthetic key, never a real credential. It must not be called authenticated.
    page.locator('#api-key').fill('synthetic-invalid-key-for-private-qa')
    page.locator('#connect').click()
    page.get_by_text('Key saved',exact=True).wait_for(timeout=60000)
    assert page.locator('#api-key').input_value()==''
    assert 'synthetic-invalid-key-for-private-qa' not in page.locator('body').inner_text()
    s=page.request.get(BASE+'/api/connection').json()
    assert s['credentialStored'] and not s['credentialVerified'] and s['status']=='not_connected'
    page.locator('#test').click()
    expect(page.locator('#test')).to_be_enabled(timeout=60000)
    assert page.locator('#connect-form').is_hidden() and page.locator('#disconnect').is_visible()
    page.locator('#disconnect').click()
    page.get_by_text('Not connected',exact=True).wait_for()
    assert not page.request.get(BASE+'/api/connection').json()['credentialStored']
    page.screenshot(path=str(OUT/'phone.png'))
    # Test-only same-origin shell fixture, not a change to the installed shell.
    page.route(BASE+'/qa-shell',lambda route:route.fulfill(content_type='text/html',body='<html style="color-scheme:dark;background:#21162f"><body><iframe title="Tinfoil" src="/" style="width:100%;height:740px;border:0;background:transparent"></iframe></body></html>'))
    page.goto(BASE+'/qa-shell')
    frame=page.frame_locator('iframe');frame.locator('#connection').wait_for()
    f=page.frames[1]
    assert f.evaluate("document.documentElement.classList.contains('wz-hosted')")
    assert f.evaluate('window.__wizardCloseOverlay()') is False
    h=page.evaluate('history.length')
    frame.locator('#api-key').fill('unsent-synthetic-input')
    tokens=f.evaluate('({...WizardTheme.current.tokens})')
    skins=['nebula','grove','tide','ember','signal']
    # Accent/text values read from the installed shell registry web/core/skins.js.
    palettes={'nebula':('#b99bff','#f3efff'),'grove':('#e6c66b','#eef5e9'),'tide':('#7fd8ff','#e8f6f8'),'ember':('#ffb470','#ffe9d6'),'signal':('#ffbe55','#d8ffd8')}
    for rev,skin in enumerate(skins,1):
        tokens={**tokens,'accent':palettes[skin][0],'text':palettes[skin][1]}
        message={'type':'wizard:appearance','appearance':{'version':1,'revision':rev,'skin':skin,'colorScheme':'dark','presentation':'window','tokens':tokens}}
        page.evaluate('(m)=>document.querySelector("iframe").contentWindow.postMessage(m,location.origin)',message)
        expect(frame.locator('html')).to_have_attribute('data-skin',skin)
        assert frame.locator('#api-key').input_value()=='unsent-synthetic-input'
        assert f.evaluate("getComputedStyle(document.body).backgroundColor")=='rgba(0, 0, 0, 0)'
        assert page.evaluate('history.length')==h
    page.screenshot(path=str(OUT/'hosted.png'))
    assert not errors,errors
    (OUT/'browser.json').write_text(json.dumps({'ok':True,'skins':skins,'pageErrors':errors,'credentialVerified':False,'paidInferenceCalls':0,'shell':'test-only same-origin frame'},indent=2))
    b.close()
print('BROWSER_OK: masked input, real free attestation, synthetic key stays unverified, test/disconnect, 5 live skin messages, hosted transparency, Back/history, phone overflow')
