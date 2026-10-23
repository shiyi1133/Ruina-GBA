#ifndef RM2K_ITEM_MASK_H
#define RM2K_ITEM_MASK_H
/* An owned-item selector is an ascending set of database IDs. Keep its
 * initial membership while a child window runs, just like the old ID vector.
 * Explicit shop buying lists retain their caller-supplied order/duplicates. */
#define ITEM_MASK_WORDS ((MAX_ITEM+31)/32)
static inline void item_mask_add(u32*mask,unsigned item){mask[(item-1)/32]|=1U<<((item-1)&31);}
static int item_mask_id(const u32*mask,int pos){unsigned word;
 for(word=0;word<ITEM_MASK_WORDS;word++){unsigned bits=mask[word],count=__builtin_popcount(bits),bit=0;
  if((unsigned)pos>=count){pos-=count;continue;}while(pos--)bits&=bits-1;
  while(!(bits&1)){bits>>=1;bit++;}return word*32+bit+1;
 }return 0;
}
#endif
