const fs = require('fs');

// Read index.html and extract the <script> content
const html = fs.readFileSync('index.html', 'utf8');
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) {
  console.error('Could not find <script> in index.html');
  process.exit(1);
}

// Evaluate the script functions in a sandbox environment
const scriptCode = scriptMatch[1];
const sandbox = {
  document: {
    getElementById: () => ({ addEventListener: () => {}, style: {} }),
    body: { appendChild: () => {}, removeChild: () => {} }
  },
  URL: { createObjectURL: () => 'blob:mock', revokeObjectURL: () => {} },
  Blob: function() {}
};

const fn = new Function('sandbox', `
  with(sandbox) {
    ${scriptCode}
    return { processMerchantRecord, parseCsvRows, serializeCsvRow };
  }
`);

const { processMerchantRecord, parseCsvRows, serializeCsvRow } = fn(sandbox);

// 1. Unit test critical merchant records
console.log('--- Testing JavaScript cleaning functions ---');

const testCases = [
  { inName: 'LA CASA DULCE INC', inEmail: 'LACASADULCE@OUTLOOK.COM', expClean: 'La Casa Dulce', expAtt: '' },
  { inName: 'ANOTHER MAN\'S TREASURE', inEmail: 'WINNINGIZAHABIT@GMAIL.COM', expClean: "Another Man's Treasure", expAtt: '' },
  { inName: '5TH AVE BARBER & SHAVE SHOP', inEmail: 'TONY_BORDONARO@YAHOO.COM', expClean: '5th Ave Barber & Shave Shop', expAtt: '' },
  { inName: 'DURHAM\'S SILT FENCING LL', inEmail: 'TIMDURHAM2009@HOTMAIL.COM', expClean: "Durham's Silt Fencing", expAtt: '' },
  { inName: 'Glacial HVAC Pro Inc.', inEmail: 'projects@glacialhvac.com', expClean: 'Glacial HVAC Pro', expAtt: '' },
  { inName: 'MD AUTO REPAIR LLC', inEmail: 'MDAUTOREPAIRLV@GMAIL.COM', expClean: 'MD Auto Repair', expAtt: '' },
  { inName: 'LOS SABORES LATINOS STOR', inEmail: 'SALVADOR.MENJIVAR2@ICLOUD.COM', expClean: 'Los Sabores Latinos Store', expAtt: '' },
  { inName: 'WAGON WHEEL RANCH HUNTIN', inEmail: 'CURT@DAKOTA-PHEASANT-HUNTING.COM', expClean: 'Wagon Wheel Ranch Hunting', expAtt: '' },
  { inName: 'do not use', inEmail: 'admin@domain.com', expClean: 'Do Not Use', expAtt: 'Attention' },
  { inName: 'FIVE ACES ADVERTISING AN', inEmail: 'FIVEACESADVERTISING@YAHOO.COM', expClean: 'Five Aces Advertising', expAtt: 'Attention' },
  { inName: 'Memorial Monuments Oak G', inEmail: 'Monumentsofla@yahoo.com', expClean: 'Memorial Monuments Oak G', expAtt: 'Attention' },
  { inName: 'OLD YELLER AUTO', inEmail: 'user@domain.com', expClean: 'Old Yeller Auto', expAtt: 'Attention' },
  { inName: 'old acct EXTREME GAME', inEmail: 'user@domain.com', expClean: 'Old Acct EXTREME GAME', expAtt: 'Attention' },
  { inName: 'The Bean Bandit (OLD)', inEmail: 'user@domain.com', expClean: 'The Bean Bandit (OLD)', expAtt: 'Attention' },
  { inName: 'Drop-N-Go Arapahoe Crossing', inEmail: 'user@domain.com', expClean: 'Drop-N-Go Arapahoe Crossing', expAtt: '' },
  { inName: 'HAIR EXPRESSIONS BY STOR', inEmail: 'STORMEPRATT@AOL.COM', expClean: 'Hair Expressions By Store', expAtt: '' },
  { inName: 'MI CASA MEXICAN RESTAURA', inEmail: 'user@domain.com', expClean: 'Mi Casa Mexican Restaurant', expAtt: '' }
];

let failed = 0;
for (const tc of testCases) {
  const res = processMerchantRecord(tc.inName, tc.inEmail);
  const cleanMatch = res.cleaned === tc.expClean;
  const attMatch = res.attention === tc.expAtt;
  if (!cleanMatch || !attMatch) {
    console.error(`FAIL: ${tc.inName}`);
    console.error(`  Expected: cleaned="${tc.expClean}", att="${tc.expAtt}"`);
    console.error(`  Received: cleaned="${res.cleaned}", att="${res.attention}"`);
    failed++;
  } else {
    console.log(`PASS: ${tc.inName} -> "${res.cleaned}" [${res.attention || 'OK'}]`);
  }
}

if (failed > 0) {
  console.error(`\n${failed} test(s) failed.`);
  process.exit(1);
} else {
  console.log(`\nAll ${testCases.length} unit test cases passed with 100% parity!`);
}
