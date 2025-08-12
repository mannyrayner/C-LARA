
from .clara_merge_glossed_and_tagged import merge_annotations_charwise, is_preseg_close_enough

text = """Jing steps into the bright real-estate office, feeling both excited and nervous. Today, she plans to begin a new chapter by renting an apartment in Australia. She meets the agent, who smiles warmly, and they sit down to discuss the lease.

The agent explains, "Jing, this lease is the agreement between you and the landlord. It outlines your rights and responsibilities as a tenant." Jing nods, understanding the importance of this document.

"You must pay a bond," the agent continues. "It’s a security deposit in case of any damage." Jing listens carefully and asks, "How much is the bond?"

"It’s usually four weeks’ rent," the agent replies. Jing agrees, knowing she has saved enough for this step.

After they both sign the lease, Jing feels relieved. She now has a place she can call home. The agent hands her the keys and says, "Welcome, Jing. Remember, as the tenant, you must take care of the apartment."

Jing smiles, thanking the agent before she heads to her new apartment. Upon arrival, she thinks about the next steps. She must transfer utilities into her name. It’s necessary to have electricity, water, and gas available from day one.

Jing also knows she must furnish the apartment. She makes a list: bed, table, and chair. "I can search online for affordable furniture," she thinks. On weekends, she plans to visit local shops.

Soon, Jing reads a reminder about the first inspection. It will happen in three months. During an inspection, the landlord checks the property to ensure it’s well maintained.

"I must keep everything clean and tidy," Jing tells herself. She begins organizing her new home, putting things in their places. Jing believes that good habits will help her at the inspection.

A week before the inspection, Jing receives a notice from the agent. It confirms the date and time. Jing asks a friend, "Can you help me prepare?" Her friend agrees, and they plan a cleaning day.

On the day of the inspection, Jing is ready. She greets the landlord and agent who arrive to assess the apartment. "You have done a good job," the landlord notes, seeing the tidy rooms and well-cared furniture.

Jing feels a sense of pride. She knows she can maintain this standard. "I must continue taking care of my home," she thinks, grateful for the assistance and support she has received.

As the day ends, Jing reflects on her journey. Signing the lease, paying the bond, arranging utilities, and preparing for the inspection—all were necessary steps for this new beginning. Every choice she made brought her closer to making this apartment her home.

Jing knows more challenges will come, but she feels prepared. With determination, she believes she can build a comfortable life in Australia. With each day, Jing embraces the adventure with hope."""

presegmented_text = """<page> Jing steps into the bright real-estate office, feeling both excited and nervous.|| Today, she plans to begin a new chapter by renting an apartment in Australia.|| She meets the agent, who smiles warmly, and they sit down to discuss the lease.||

The agent explains, "Jing, this lease is the agreement between you and the landlord.|| It outlines your rights and responsibilities as a tenant."|| Jing nods, understanding the importance of this document.||

<page> "You must pay a bond," the agent continues.|| "It’s a security deposit in case of any damage."|| Jing listens carefully and asks, "How much is the bond?"||

"It’s usually four weeks’ rent," the agent replies.|| Jing agrees, knowing she has saved enough for this step.||

After they both sign the lease, Jing feels relieved.|| She now has a place she can call home.|| The agent hands her the keys and says, "Welcome, Jing.|| Remember, as the tenant, you must take care of the apartment."||

<page> Jing smiles, thanking the agent before she heads to her new apartment.|| Upon arrival, she thinks about the next steps.|| She must transfer utilities into her name.|| It’s necessary to have electricity, water, and gas available from day one.||

Jing also knows she must furnish the apartment.|| She makes a list: bed, table, and chair.|| "I can search online for affordable furniture," she thinks.|| On weekends, she plans to visit local shops.||

<page> Soon, Jing reads a reminder about the first inspection.|| It will happen in three months.|| During an inspection, the landlord checks the property to ensure it’s well maintained.||

"I must keep everything clean and tidy," Jing tells herself.|| She begins organizing her new home, putting things in their places.|| Jing believes that good habits will help her at the inspection.||

<page> A week before the inspection, Jing receives a notice from the agent.|| It confirms the date and time.|| Jing asks a friend, "Can you help me prepare?"|| Her friend agrees, and they plan a cleaning day.||

On the day of the inspection, Jing is ready.|| She greets the landlord and agent who arrive to assess the apartment.|| "You have done a good job," the landlord notes, seeing the tidy rooms and well-cared furniture.||

<page> Jing feels a sense of pride.|| She knows she can maintain this standard.|| "I must continue taking care of my home," she thinks, grateful for the assistance and support she has received.||

As the day ends, Jing reflects on her journey.|| Signing the lease, paying the bond, arranging utilities, and preparing for the inspection—all were necessary steps for this new beginning.|| Every choice she made brought her closer to making this apartment her home.||

Jing knows more challenges will come, but she feels prepared.|| With determination, she believes she can build a comfortable life in Australia.|| With each day, Jing embraces the adventure with hope.||"""

def test():
    presegmented_text1 = merge_annotations_charwise(text, presegmented_text, 'presegmentation')
    print(presegmented_text1)

def test_check():
    ok, ratio = is_preseg_close_enough(text, presegmented_text)
    print(presegmented_text1)

    
