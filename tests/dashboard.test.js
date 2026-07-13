const test = require('node:test');
const assert = require('node:assert/strict');

const {
  getSplit,
  filterAttempts,
  summarizeAttempts,
  sortPlayersByVolume,
  paginate,
  summarizeValidation,
} = require('../app.js');

const attempts = [
  { player_name: 'Stephen Curry', segment: 'Regular Season', venue: 'home', position: '1 of 2', interrupted: false, made: true, description: 'makes free throw 1 of 2' },
  { player_name: 'Stephen Curry', segment: 'Play-In', venue: 'away', position: '2 of 2', interrupted: true, made: false, description: 'misses free throw 2 of 2' },
  { player_name: 'Jimmy Butler III', segment: 'Regular Season', venue: 'away', position: '1 of 1', interrupted: false, made: true, description: 'makes technical free throw' },
];

test('getSplit returns the named split and a safe empty value when missing', () => {
  const splits = [{ split: 'overall', makes: 8, attempts: 10, pct: 80 }];
  assert.deepEqual(getSplit(splits, 'overall'), splits[0]);
  assert.deepEqual(getSplit(splits, 'clutch'), { split: 'clutch', makes: 0, attempts: 0, misses: 0, pct: null });
});

test('filterAttempts combines player, segment, venue, position, interruption, and text filters', () => {
  const result = filterAttempts(attempts, {
    player: 'Stephen Curry',
    segment: 'Play-In',
    venue: 'away',
    position: '2 of 2',
    interrupted: 'yes',
    search: 'misses',
  });
  assert.equal(result.length, 1);
  assert.equal(result[0].made, false);
});

test('summarizeAttempts calculates makes, attempts, misses, and percentage', () => {
  assert.deepEqual(summarizeAttempts(attempts), { makes: 2, attempts: 3, misses: 1, pct: 66.7 });
});

test('sortPlayersByVolume orders players by overall attempts descending', () => {
  const players = [
    { player_name: 'A', splits: [{ split: 'overall', attempts: 10 }] },
    { player_name: 'B', splits: [{ split: 'overall', attempts: 30 }] },
  ];
  assert.deepEqual(sortPlayersByVolume(players).map((player) => player.player_name), ['B', 'A']);
});

test('paginate clamps page boundaries and returns page metadata', () => {
  const result = paginate([1, 2, 3, 4, 5], 4, 2);
  assert.deepEqual(result.items, [5]);
  assert.equal(result.page, 3);
  assert.equal(result.pages, 3);
  assert.equal(result.total, 5);
});

test('summarizeValidation counts reconciled games from validation rows', () => {
  assert.deepEqual(summarizeValidation([{ passed: true }, { passed: true }, { passed: false }]), { passed: 2, total: 3 });
});
