import type { Domain } from '@/theme';

export type Exercise = {
  id: string;
  name: string;
  sets: number;
  /** Target reps or duration, as the plan writes it. */
  target: string;
  /** Cable-machine exercises are grouped together in the session view. */
  cable?: boolean;
};

export type WorkoutDay = {
  /** 0 = Sunday … 6 = Saturday, matching Date#getDay. */
  weekday: number;
  title: string;
  focus: string;
  domain: Domain;
  warmup: string[];
  exercises: Exercise[];
  abFinisher?: boolean;
};

const ex = (id: string, name: string, sets: number, target: string, cable = false): Exercise => ({
  id, name, sets, target, cable,
});

export const WORKOUTS: WorkoutDay[] = [
  {
    weekday: 1, title: 'Glutes + Hamstrings', focus: 'Glute hypertrophy · Hip width', domain: 'fitness',
    warmup: ['Glute bridge × 15', 'Banded lateral walk × 10 each way', 'Leg swings × 10 each'],
    abFinisher: true,
    exercises: [
      ex('hip-thrust', 'Barbell Hip Thrust', 4, '10–12'),
      ex('rdl', 'Romanian Deadlift (RDL)', 3, '10–12'),
      ex('bss', 'Bulgarian Split Squat', 3, '10 each'),
      ex('cable-kickback', 'Cable Kickback', 3, '15 each', true),
      ex('sumo-dl', 'Sumo Deadlift', 3, '10'),
      ex('abductor', 'Abductor Machine', 3, '20'),
      ex('glute-hyper', 'Glute Hyperextension', 3, '15'),
    ],
  },
  {
    weekday: 2, title: 'Upper Body + Core', focus: 'V-taper · Slim defined arms', domain: 'mind',
    warmup: ['Arm circles × 20', 'Band pull-apart × 15', 'Cat-cow × 10'],
    exercises: [
      ex('lat-pulldown', 'Lat Pulldown', 3, '12', true),
      ex('cable-row', 'Seated Cable Row', 3, '12', true),
      ex('db-press', 'Dumbbell Shoulder Press', 3, '12'),
      ex('lat-raise', 'Lateral Raises (cable)', 3, '15', true),
      ex('tri-pushdown', 'Tricep Pushdown — rope', 3, '15', true),
      ex('bicep-curl', 'Bicep Curl — alternating DB', 3, '12'),
      ex('cable-crunch', 'Cable Crunch — kneeling', 3, '15', true),
      ex('dead-bug', 'Dead Bug', 3, '10 each'),
      ex('plank-ppt', 'Plank — posterior pelvic tilt', 3, '45s'),
    ],
  },
  {
    weekday: 3, title: 'Quads + Inner Thigh', focus: 'Inner thigh tone · Quad definition', domain: 'nutrition',
    warmup: ['Bodyweight squat × 15', 'Side lunge × 8 each', 'Ankle rocks × 10 each'],
    exercises: [
      ex('goblet-squat', 'Goblet Squat', 4, '12'),
      ex('leg-press', 'Leg Press — narrow foot placement', 3, '15'),
      ex('adductor', 'Adductor Machine', 4, '20'),
      ex('sumo-goblet', 'Sumo Goblet Squat', 3, '15'),
      ex('leg-ext', 'Leg Extension', 3, '15'),
      ex('walking-lunge', 'Walking Lunges', 3, '12 each'),
      ex('leg-curl', 'Lying Leg Curl', 3, '12'),
    ],
  },
  {
    weekday: 5, title: 'Full Body + Glutes', focus: 'Fat burn · Glute finisher', domain: 'foundation',
    warmup: ['Glute bridge × 15', 'Inchworm × 6', 'Bodyweight squat × 12'],
    abFinisher: true,
    exercises: [
      ex('back-squat', 'Barbell Back Squat', 4, '8–10'),
      ex('db-row', 'Dumbbell Row — one knee on bench', 3, '12 each'),
      ex('db-chest', 'Dumbbell Chest Press', 3, '12'),
      ex('step-up', 'Step-Ups with Dumbbells', 3, '12 each'),
      ex('pull-through', 'Cable Pull-Through', 3, '15', true),
      ex('sl-hip-thrust', 'Single-Leg Hip Thrust', 3, '12 each'),
      ex('face-pull', 'Face Pull — cable rope at eye level', 3, '15', true),
    ],
  },
  {
    weekday: 6, title: 'Arms + Abs', focus: 'Arm definition · Flat stomach · 45 min', domain: 'appearance',
    warmup: ['Arm circles × 20', 'Band pull-apart × 15', 'Dead hang 20s'],
    abFinisher: true,
    exercises: [
      ex('oh-tri', 'Overhead Tricep Extension', 3, '15'),
      ex('bench-dip', 'Tricep Dips — bench, feet elevated', 3, '15'),
      ex('hammer', 'Hammer Curl', 3, '12'),
      ex('cable-curl', 'Cable Bicep Curl', 3, '15', true),
      ex('hanging-knee', 'Hanging Knee Raise', 3, '15'),
      ex('ab-wheel', 'Ab Wheel Rollout — from knees', 3, '10'),
      ex('side-plank', 'Side Plank', 3, '30s each'),
      ex('rev-crunch', 'Reverse Crunch', 3, '15'),
    ],
  },
];

export const AB_FINISHER: Exercise[] = [
  ex('af-hanging-leg', 'Hanging Leg Raise', 4, '12'),
  ex('af-ab-wheel', 'Ab Wheel Rollout', 4, '8–12'),
  ex('af-cable-crunch', 'Cable Crunch', 4, '15', true),
  ex('af-rev-crunch', 'Reverse Crunch', 3, '15'),
  ex('af-hollow', 'Hollow Body Hold', 3, '30–45s'),
];

export const PROGRESSIVE_OVERLOAD =
  'Every 2 weeks — increase weight by the smallest increment OR add 1–2 reps. Log your weights.';

export function workoutFor(weekday: number): WorkoutDay | undefined {
  return WORKOUTS.find((w) => w.weekday === weekday);
}

export function restDayLabel(weekday: number): string {
  return weekday === 4 ? 'Active rest — walk' : 'Rest — the river keeps moving';
}

/** Session order: free-weight/machine work first, then cable work together. */
export function sessionOrder(exercises: Exercise[]): Exercise[] {
  return [...exercises.filter((e) => !e.cable), ...exercises.filter((e) => e.cable)];
}
