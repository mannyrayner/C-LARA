from .clara_classes import Text, Page, Segment, ContentElement

def add_acknowledgements_to_text_object(text_object, acknowledgements_info):
    if not acknowledgements_info:
        return

    short_text = acknowledgements_info.short_text
    long_text = acknowledgements_info.long_text
    long_text_location = acknowledgements_info.long_text_location

    if long_text:
        acknowlegements_content_element = ContentElement('NonWordText', long_text)
        acknowlegements_segment = Segment([acknowlegements_content_element])
        if long_text_location == 'first_page':
            # Add the long acknowledgements text to the end of the first page
            first_page = text_object.pages[0]
            first_page.segments += [ acknowlegements_segment ]
            # Add the short acknowledgement to everything except the first page
            pages_for_short_acknowledgement = text_object.pages[1:]
        else:
            # Alternative: add it in extra page at end
            new_page = Page([ acknowlegements_segment ] )
            text_object.pages += [ new_page ]
            # Add the short acknowledgement to everything except the last page
            pages_for_short_acknowledgement = text_object.pages[:-1]
    else:
        # Add the short acknowledgement to everything
        pages_for_short_acknowledgement = text_object.pages
            
    if short_text:
        for page in pages_for_short_acknowledgement:
            page.annotations['acknowledgements'] = short_text

